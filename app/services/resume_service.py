"""
简历服务模块
处理简历上传下载相关的业务逻辑
"""

import io
import os
import re
from flask import send_file


class ResumeService:
    """简历服务类"""
    
    @staticmethod
    def _extract_text_from_image_bytes(image_bytes, mimetype, filename):
        """调用LLM Vision接口提取图片中的招聘岗位信息或文字内容"""
        from flask import current_app
        from openai import OpenAI
        import base64
        
        api_key = current_app.config.get('VISION_API_KEY') or current_app.config['OPENAI_API_KEY']
        base_url = current_app.config.get('VISION_BASE_URL') or current_app.config['OPENAI_BASE_URL']
        
        client = OpenAI(
            api_key=api_key,
            base_url=base_url
        )
        
        img_base64 = base64.b64encode(image_bytes).decode('utf-8')
        
        if not mimetype or 'image' not in mimetype:
            mimetype = 'image/jpeg'
            
        prompt = """你是一个专业的文字提取和招聘专家。请从这张工作岗位招聘截图（如Boss直聘、猎聘、拉勾等招聘软件截图，或简历图片）中，准确提取并整理出所有的文字内容。
如果这是招聘岗位信息，请务必详细整理出：
1. 岗位名称
2. 职责描述
3. 任职资格/要求
4. 薪资待遇及工作地点等其他核心信息

请将提取出的信息以清晰可读的格式输出。如果是普通简历图片，请直接完整提取简历上的个人信息、求职意向和工作经历等。只输出提取和整理后的文本，不需要包含任何解释。"""

        # 收集可能支持多模态的候选模型列表
        configured_model = current_app.config.get('VISION_MODEL') or current_app.config['OPENAI_MODEL']
        models_to_try = [configured_model]
        
        # 尝试获取当前密钥支持的全部模型，筛选出多模态模型
        api_models = []
        try:
            model_list = client.models.list()
            api_models = [m.id for m in model_list.data]
        except Exception:
            pass
            
        vision_keywords = ['vision', 'vl', 'gpt-4o', 'claude-3-5', 'gemini-1.5', 'multimodal']
        for m_id in api_models:
            if any(kw in m_id.lower() for kw in vision_keywords):
                if m_id not in models_to_try:
                    models_to_try.append(m_id)
                    
        # 常见模型兜底
        for fallback in ["gpt-4o-mini", "gpt-4o", "gpt-4-vision-preview"]:
            if fallback not in models_to_try:
                models_to_try.append(fallback)
                
        last_err = None
        for model_name in models_to_try:
            if not model_name:
                continue
            try:
                response = client.chat.completions.create(
                    model=model_name,
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": prompt},
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:{mimetype};base64,{img_base64}"
                                    }
                                }
                            ]
                        }
                    ],
                    max_tokens=1500,
                    temperature=0.1
                )
                return response.choices[0].message.content.strip()
            except Exception as e:
                last_err = e
                continue
                
        available_models_str = ", ".join(api_models) if api_models else "获取失败"
        raise RuntimeError(
            f"多模态大模型解析失败。\n"
            f"已尝试模型列表: {models_to_try}\n"
            f"最后一次尝试报错: {str(last_err)}\n"
            f"该 API 密钥支持的所有模型列表: [{available_models_str}]。若列表包含其他支持图片的模型，请在 .env 中进行配置。"
        )

    @staticmethod
    def upload_resume(file):
        """上传文件（简历/图片/文档），解析并返回文本内容"""
        if not file or file.filename == '':
            return {"success": False, "error": "未选择文件"}
        
        allowed_extensions = {'.pdf', '.docx', '.doc', '.txt', '.png', '.jpg', '.jpeg', '.webp', '.bmp'}
        ext = os.path.splitext(file.filename)[1].lower()
        if ext not in allowed_extensions:
            return {"success": False, "error": "不支持的文件格式，请上传PDF、DOCX、TXT或图片文件"}
        
        try:
            text_content = ""
            file_bytes = file.read()
            if not file_bytes:
                return {"success": False, "error": "文件内容为空"}
            
            is_image = ext in {'.png', '.jpg', '.jpeg', '.webp', '.bmp'}
            
            if is_image:
                text_content = ResumeService._extract_text_from_image_bytes(file_bytes, file.content_type, file.filename)
            
            elif ext == '.pdf':
                from pypdf import PdfReader
                reader = PdfReader(io.BytesIO(file_bytes))
                
                # 1. 尝试标准文本提取
                for page in reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text_content += page_text + "\n"
                
                # 2. 如果文本为空，尝试提取表单字段与注释
                if not text_content.strip():
                    fields = reader.get_fields()
                    if fields:
                        for field_name, field_val in fields.items():
                            if isinstance(field_val, dict) and field_val.get('/V'):
                                text_content += f"{field_name}: {field_val['/V']}\n"
                            elif hasattr(field_val, 'get') and field_val.get('/V'):
                                text_content += f"{field_name}: {field_val.get('/V')}\n"
                    
                    for page in reader.pages:
                        if '/Annots' in page:
                            for annot in page['/Annots']:
                                try:
                                    annot_obj = annot.get_object()
                                    if '/Contents' in annot_obj:
                                        text_content += str(annot_obj['/Contents']) + "\n"
                                except Exception:
                                    continue
                
                # 3. 如果文本仍然为空，尝试使用大模型 Vision OCR 解析 PDF 中的图片 (扫描件 PDF)
                if not text_content.strip():
                    extracted_images_text = ""
                    image_count = 0
                    for page_idx, page in enumerate(reader.pages):
                        page_images = list(page.images)
                        for img_idx, img in enumerate(page_images[:3]):
                            try:
                                img_bytes = img.data
                                img_name = img.name or f"page_{page_idx}_img_{img_idx}"
                                img_ext = os.path.splitext(img_name)[1].lower()
                                img_mimetype = "image/png" if img_ext == ".png" else "image/jpeg"
                                
                                img_text = ResumeService._extract_text_from_image_bytes(
                                    img_bytes, 
                                    img_mimetype, 
                                    f"PDF_Page_{page_idx+1}_Image_{img_idx+1}"
                                )
                                if img_text:
                                    extracted_images_text += f"\n--- [PDF第 {page_idx+1} 页提取内容] ---\n{img_text}\n"
                                    image_count += 1
                                    if image_count >= 5: # 最多处理 5 张图片，防止大模型接口超时
                                        break
                            except Exception:
                                continue
                        if image_count >= 5:
                            break
                    text_content = extracted_images_text
            
            elif ext in ('.docx', '.doc'):
                from docx import Document
                doc = Document(io.BytesIO(file_bytes))
                for para in doc.paragraphs:
                    text_content += para.text + "\n"
            
            elif ext == '.txt':
                text_content = file_bytes.decode('utf-8')
            
            if not text_content.strip():
                return {"success": False, "error": "文件内容为空或无法解析，请确保文件包含文字或清晰可读的截图"}
            
            return {
                "success": True,
                "data": {
                    "filename": file.filename,
                    "content": text_content.strip(),
                    "file_type": ext
                }
            }
        
        except Exception as e:
            return {"success": False, "error": f"文件解析失败: {str(e)}"}
    
    @staticmethod
    def download_resume(content, filename, file_format):
        """将简历内容转换为文件下载"""
        if not content:
            return {"success": False, "error": "内容不能为空"}
        
        try:
            # 检测是否为HTML格式
            is_html = content.strip().startswith('<!DOCTYPE html>') or content.strip().startswith('<html')
            
            if file_format == 'html':
                # 直接导出HTML文件
                buffer = io.BytesIO(content.encode('utf-8'))
                return {
                    "success": True,
                    "file": send_file(
                        buffer,
                        as_attachment=True,
                        download_name=f'{filename}.html',
                        mimetype='text/html'
                    )
                }
            
            elif file_format == 'pdf':
                # 生成PDF格式 - 使用xhtml2pdf（纯Python，无需系统依赖）
                from xhtml2pdf import pisa
                
                if is_html:
                    html_content = content
                else:
                    # Markdown转HTML，保留基本样式
                    html_content = content
                    html_content = re.sub(
                        r'^# (.+)$', 
                        r'<h1 style="font-size:20px;color:#333;border-bottom:2px solid #4285f4;padding-bottom:8px;">\1</h1>', 
                        html_content, flags=re.MULTILINE
                    )
                    html_content = re.sub(
                        r'^## (.+)$', 
                        r'<h2 style="font-size:16px;color:#4285f4;margin-top:20px;">\1</h2>', 
                        html_content, flags=re.MULTILINE
                    )
                    html_content = re.sub(
                        r'^### (.+)$', 
                        r'<h3 style="font-size:14px;color:#555;">\1</h3>', 
                        html_content, flags=re.MULTILINE
                    )
                    html_content = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html_content)
                    html_content = re.sub(
                        r'^- (.+)$', 
                        r'<li style="margin:4px 0;">\1</li>', 
                        html_content, flags=re.MULTILINE
                    )
                    html_content = re.sub(
                        r'(<li.*?</li>)', 
                        r'<ul style="padding-left:20px;">\1</ul>', 
                        html_content, flags=re.DOTALL
                    )
                    html_content = html_content.replace('\n', '<br>')
                    html_content = f'''<!DOCTYPE html>
<html><head><meta charset="utf-8"></head>
<body style="font-family:'Microsoft YaHei','SimSun',Arial,sans-serif;font-size:12pt;line-height:1.8;padding:20px;color:#333;">
{html_content}
</body></html>'''
                
                # 确保HTML包含中文字体声明
                if '<style' not in html_content:
                    # 在head中添加字体样式
                    html_content = html_content.replace(
                        '<head>',
                        '<head><style>@page { size: A4; margin: 2cm; } body { font-family: "Microsoft YaHei", "SimSun", "STSong", Arial, sans-serif; }</style>'
                    )
                
                buffer = io.BytesIO()
                pisa_status = pisa.CreatePDF(html_content, dest=buffer, encoding='utf-8')
                
                if pisa_status.err:
                    return {"success": False, "error": "PDF生成失败"}
                
                buffer.seek(0)
                
                return {
                    "success": True,
                    "file": send_file(
                        buffer,
                        as_attachment=True,
                        download_name=f'{filename}.pdf',
                        mimetype='application/pdf'
                    )
                }
            
            elif file_format == 'docx':
                # Markdown格式转DOCX
                from docx import Document
                from docx.shared import Pt
                
                doc = Document()
                
                style = doc.styles['Normal']
                style.font.name = 'Arial'
                style.font.size = Pt(11)
                
                lines = content.split('\n')
                for line in lines:
                    line = line.strip()
                    if not line:
                        doc.add_paragraph('')
                        continue
                    
                    if line.startswith('# '):
                        doc.add_heading(line[2:].strip(), level=1)
                    elif line.startswith('## '):
                        doc.add_heading(line[3:].strip(), level=2)
                    elif line.startswith('### '):
                        doc.add_heading(line[4:].strip(), level=3)
                    elif line.startswith('- ') or line.startswith('* '):
                        doc.add_paragraph(line[2:].strip(), style='List Bullet')
                    elif line.startswith('**') and line.endswith('**'):
                        p = doc.add_paragraph()
                        run = p.add_run(line[2:-2].strip())
                        run.bold = True
                    else:
                        p = doc.add_paragraph(line)
                        if '**' in line:
                            parts = line.split('**')
                            p.clear()
                            for i, part in enumerate(parts):
                                run = p.add_run(part)
                                if i % 2 == 1:
                                    run.bold = True
                
                buffer = io.BytesIO()
                doc.save(buffer)
                buffer.seek(0)
                
                return {
                    "success": True,
                    "file": send_file(
                        buffer,
                        as_attachment=True,
                        download_name=f'{filename}.docx',
                        mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
                    )
                }
            
            else:
                return {"success": False, "error": "暂只支持HTML、PDF和DOCX格式"}
        
        except Exception as e:
            return {"success": False, "error": f"生成文件失败: {str(e)}"}
