"""
公告PDF文本提取器
优先级：PyMuPDF → pdfplumber → pypdf
不做OCR
"""
from pathlib import Path
from typing import Optional, Tuple


class AnnouncementPdfTextExtractor:
    """
    公告PDF文本提取器

    方法优先级：
    1. PyMuPDF (fitz) - 快速、准确
    2. pdfplumber - fallback
    3. pypdf - 最后fallback

    不做OCR，不处理图片PDF
    """

    def __init__(self, max_pages: int = 10):
        """
        初始化

        Args:
            max_pages: 最多提取页数
        """
        self.max_pages = max_pages

    def extract(self, pdf_path: str) -> dict:
        """
        提取PDF文本

        Args:
            pdf_path: PDF文件路径

        Returns:
            {
                'status': 'success/failed',
                'text': '...',
                'text_length': int,
                'method': 'pymupdf/pdfplumber/pypdf',
                'error': '...'
            }
        """
        if not Path(pdf_path).exists():
            return {
                'status': 'failed',
                'text': '',
                'text_length': 0,
                'method': '',
                'error': 'PDF文件不存在'
            }

        # 1. 尝试PyMuPDF
        result = self._extract_with_pymupdf(pdf_path)
        if result['status'] == 'success' and result['text_length'] >= 100:
            return result

        # 2. Fallback: pdfplumber
        result = self._extract_with_pdfplumber(pdf_path)
        if result['status'] == 'success' and result['text_length'] >= 100:
            return result

        # 3. Fallback: pypdf
        result = self._extract_with_pypdf(pdf_path)
        return result

    def _extract_with_pymupdf(self, pdf_path: str) -> dict:
        """使用PyMuPDF提取"""
        try:
            import fitz  # PyMuPDF

            doc = fitz.open(pdf_path)
            text_parts = []

            for page_num in range(min(len(doc), self.max_pages)):
                page = doc[page_num]
                text = page.get_text("text")
                text_parts.append(text)

            doc.close()

            full_text = "\n".join(text_parts)
            cleaned_text = self._clean_text(full_text)

            return {
                'status': 'success',
                'text': cleaned_text,
                'text_length': len(cleaned_text),
                'method': 'pymupdf',
                'error': ''
            }

        except ImportError:
            return {
                'status': 'failed',
                'text': '',
                'text_length': 0,
                'method': '',
                'error': 'PyMuPDF未安装'
            }
        except Exception as e:
            return {
                'status': 'failed',
                'text': '',
                'text_length': 0,
                'method': '',
                'error': f'PyMuPDF错误: {str(e)}'
            }

    def _extract_with_pdfplumber(self, pdf_path: str) -> dict:
        """使用pdfplumber提取"""
        try:
            import pdfplumber

            with pdfplumber.open(pdf_path) as pdf:
                text_parts = []

                for page_num in range(min(len(pdf.pages), self.max_pages)):
                    page = pdf.pages[page_num]
                    text = page.extract_text()
                    if text:
                        text_parts.append(text)

            full_text = "\n".join(text_parts)
            cleaned_text = self._clean_text(full_text)

            return {
                'status': 'success',
                'text': cleaned_text,
                'text_length': len(cleaned_text),
                'method': 'pdfplumber',
                'error': ''
            }

        except ImportError:
            return {
                'status': 'failed',
                'text': '',
                'text_length': 0,
                'method': '',
                'error': 'pdfplumber未安装'
            }
        except Exception as e:
            return {
                'status': 'failed',
                'text': '',
                'text_length': 0,
                'method': '',
                'error': f'pdfplumber错误: {str(e)}'
            }

    def _extract_with_pypdf(self, pdf_path: str) -> dict:
        """使用pypdf提取"""
        try:
            from pypdf import PdfReader

            reader = PdfReader(pdf_path)
            text_parts = []

            for page_num in range(min(len(reader.pages), self.max_pages)):
                page = reader.pages[page_num]
                text = page.extract_text()
                if text:
                    text_parts.append(text)

            full_text = "\n".join(text_parts)
            cleaned_text = self._clean_text(full_text)

            return {
                'status': 'success',
                'text': cleaned_text,
                'text_length': len(cleaned_text),
                'method': 'pypdf',
                'error': ''
            }

        except ImportError:
            return {
                'status': 'failed',
                'text': '',
                'text_length': 0,
                'method': '',
                'error': 'pypdf未安装'
            }
        except Exception as e:
            return {
                'status': 'failed',
                'text': '',
                'text_length': 0,
                'method': '',
                'error': f'pypdf错误: {str(e)}'
            }

    def _clean_text(self, text: str) -> str:
        """清洗文本"""
        # 去除多余空行
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        # 重新组合
        cleaned = '\n'.join(lines)
        # 去除连续空格
        cleaned = ' '.join(cleaned.split())
        return cleaned


__all__ = ['AnnouncementPdfTextExtractor']
