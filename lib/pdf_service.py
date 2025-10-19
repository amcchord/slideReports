"""
PDF generation service for converting HTML reports to PDF.
"""
from weasyprint import HTML
import io
import logging

logger = logging.getLogger(__name__)


class PDFService:
    """Service for converting HTML to PDF"""
    
    @staticmethod
    def _inject_width_css(html_content: str) -> str:
        """
        Inject CSS to set explicit rendering width for PDF.
        WeasyPrint doesn't use viewport meta tags, so we need explicit CSS widths.
        
        Args:
            html_content: Original HTML content
            
        Returns:
            HTML with injected width CSS
        """
        width_css = """
        <style>
            @page {
                size: 1600px 2400px;
                margin: 0.25in;
            }
            
            body {
                width: 100%;
                margin: 0 auto;
            }
            
        </style>
        """
        
        # Try to inject before closing </head> tag
        if '</head>' in html_content:
            html_content = html_content.replace('</head>', f'{width_css}</head>')
        elif '<body>' in html_content:
            # If no </head>, inject before <body>
            html_content = html_content.replace('<body>', f'{width_css}<body>')
        else:
            # Otherwise just prepend it
            html_content = width_css + html_content
        
        return html_content
    
    @staticmethod
    def html_to_pdf(html_content: str) -> bytes:
        """
        Convert HTML report to PDF bytes.
        
        Args:
            html_content: Complete HTML document as string
            
        Returns:
            PDF as bytes for email attachment
            
        Raises:
            Exception: If PDF generation fails
        """
        try:
            # Inject CSS to set explicit rendering width for WeasyPrint
            html_content = PDFService._inject_width_css(html_content)
            
            # Create a BytesIO buffer to store the PDF
            pdf_buffer = io.BytesIO()
            
            # Convert HTML to PDF with explicit width CSS and DPI
            # WeasyPrint can handle base64 encoded images in the HTML
            # Zoom set to 0.5 to render at 50% scale
            HTML(string=html_content).write_pdf(pdf_buffer, zoom=0.5)
            
            # Get the PDF bytes
            pdf_bytes = pdf_buffer.getvalue()
            pdf_buffer.close()
            
            logger.info(f"PDF generated successfully ({len(pdf_bytes)} bytes)")
            return pdf_bytes
            
        except Exception as e:
            logger.error(f"Failed to generate PDF: {str(e)}")
            raise Exception(f"PDF generation failed: {str(e)}")

