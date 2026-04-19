"""
Delegates Module

Contains custom Qt delegates for rendering table cells.
"""

from PySide6.QtWidgets import QStyledItemDelegate, QStyle
from PySide6.QtCore import Qt
from PySide6.QtGui import QTextDocument


class HTMLDelegate(QStyledItemDelegate):
    """
    Custom delegate to render HTML in table cells.
    
    This delegate allows table cells to display formatted HTML content
    including colored text, bold, italic, and other HTML formatting.
    
    Usage:
        table = QTableWidget()
        delegate = HTMLDelegate()
        table.setItemDelegate(delegate)
        
        # Now cells can contain HTML
        item = QTableWidgetItem("<b style='color:green'>+100.00</b>")
        table.setItem(0, 0, item)
    """
    
    def paint(self, painter, option, index):
        """
        Paint the cell with HTML rendering.
        
        Args:
            painter: QPainter for drawing
            option: QStyleOptionViewItem with cell options
            index: QModelIndex of the cell
        """
        # Handle selection highlight
        if option.state & QStyle.State_Selected:
            painter.fillRect(option.rect, option.palette.highlight())
        
        # Get cell text
        text = index.data(Qt.DisplayRole)
        if text:
            doc = QTextDocument()
            doc.setHtml(str(text))
            doc.setTextWidth(option.rect.width())
            
            painter.save()
            painter.translate(option.rect.topLeft())
            doc.drawContents(painter)
            painter.restore()
    
    def sizeHint(self, option, index):
        """
        Get the size hint for the cell.
        
        Args:
            option: QStyleOptionViewItem with cell options
            index: QModelIndex of the cell
        
        Returns:
            Recommended size for the cell
        """
        text = index.data(Qt.DisplayRole)
        if text:
            doc = QTextDocument()
            doc.setHtml(str(text))
            doc.setTextWidth(option.rect.width())
            return doc.size().toSize()
        
        return super().sizeHint(option, index)


class ColoredTextDelegate(QStyledItemDelegate):
    """
    Delegate for rendering colored text based on value.
    
    Positive values are shown in green, negative in red.
    """
    
    def __init__(self, positive_color: str = "#228B22", negative_color: str = "#DC143C", parent=None):
        """
        Initialize the delegate.
        
        Args:
            positive_color: Color for positive values (default green)
            negative_color: Color for negative values (default red)
            parent: Parent widget
        """
        super().__init__(parent)
        self.positive_color = positive_color
        self.negative_color = negative_color
    
    def paint(self, painter, option, index):
        """Paint the cell with colored text."""
        if option.state & QStyle.State_Selected:
            painter.fillRect(option.rect, option.palette.highlight())
        
        text = index.data(Qt.DisplayRole)
        if text:
            # Try to determine if value is positive or negative
            try:
                # Remove currency symbols and commas for parsing
                clean_text = str(text).replace('₹', '').replace(',', '').replace('+', '').strip()
                value = float(clean_text)
                
                if value > 0:
                    color = self.positive_color
                elif value < 0:
                    color = self.negative_color
                else:
                    color = "#FFFFFF"  # White for zero
                
                html = f"<span style='color:{color}'>{text}</span>"
                doc = QTextDocument()
                doc.setHtml(html)
                doc.setTextWidth(option.rect.width())
                
                painter.save()
                painter.translate(option.rect.topLeft())
                doc.drawContents(painter)
                painter.restore()
                return
            except:
                pass
        
        # Fallback to default painting
        super().paint(painter, option, index)
