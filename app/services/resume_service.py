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
    def upload_resume(file):
        """上传简历文件，解析并返回文本内容"""
        if not file or file.filename == '':
            return {"success": False, "error": "未选择文件"}
        
        allowed_extensions = {'.pdf', '.docx', '.doc', '.txt'}
        ext = os.path.splitext(file.filename)[1].lower()
        if ext not in allowed_extensions:
            return {"success": False, "error": "不支持的文件格式，请上传PDF、DOCX或TXT文件"}
        
        try:
            text_content = ""
            
            if ext == '.pdf':
                from pypdf import PdfReader
                reader = PdfReader(io.BytesIO(file.read()))
                for page in reader.pages:
                    text_content += page.extract_text() + "\n"
            
            elif ext in ('.docx', '.doc'):
                from docx import Document
                doc = Document(io.BytesIO(file.read()))
                for para in doc.paragraphs:
                    text_content += para.text + "\n"
            
            elif ext == '.txt':
                text_content = file.read().decode('utf-8')
            
            if not text_content.strip():
                return {"success": False, "error": "文件内容为空或无法解析"}
            
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
                # 生成PDF格式 - 使用weasyprint保留HTML样式
                from weasyprint import HTML
                
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
                
                buffer = io.BytesIO()
                HTML(string=html_content).write_pdf(buffer)
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
