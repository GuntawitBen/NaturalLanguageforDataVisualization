import { useState, useEffect, useCallback } from 'react';
import { X, Download, Loader2 } from 'lucide-react';
import html2canvas from 'html2canvas';
import { jsPDF } from 'jspdf';

const A4_WIDTH_PT = 595.28;
const A4_HEIGHT_PT = 841.89;

export default function PdfExportModal({ open, onClose, dashboardTitle }) {
  const [pages, setPages] = useState([]);
  const [loading, setLoading] = useState(true);
  const [pdfDoc, setPdfDoc] = useState(null);

  const capture = useCallback(async () => {
    const grid = document.querySelector('.dashboard-grid');
    if (!grid) return;

    grid.classList.add('pdf-capture-mode');

    try {
      const canvas = await html2canvas(grid, {
        scale: 2,
        useCORS: true,
        backgroundColor: '#ffffff',
        logging: false,
      });

      const imgWidth = canvas.width;
      const imgHeight = canvas.height;
      const scale = canvas.width / grid.offsetWidth; // html2canvas scale factor
      const pageRatio = A4_HEIGHT_PT / A4_WIDTH_PT;
      const pageHeightPx = imgWidth * pageRatio;

      // Get card positions (in canvas pixel space) to avoid splitting them
      const gridRect = grid.getBoundingClientRect();
      const cards = Array.from(grid.querySelectorAll('.dashboard-grid-item'));
      const cardBounds = cards.map((card) => {
        const r = card.getBoundingClientRect();
        return {
          top: (r.top - gridRect.top) * scale,
          bottom: (r.bottom - gridRect.top) * scale,
        };
      }).sort((a, b) => a.top - b.top);

      // Build smart page breaks that don't cut through cards
      const pageBreaks = [0]; // start of each page (in canvas Y px)
      let cursor = 0;
      while (cursor + pageHeightPx < imgHeight) {
        let breakY = cursor + pageHeightPx;

        // Repeatedly adjust breakY upward until no card is cut
        let changed = true;
        while (changed) {
          changed = false;
          for (const card of cardBounds) {
            // Card straddles the break line: starts on this page, ends past breakY
            if (card.top >= cursor && card.top < breakY && card.bottom > breakY) {
              breakY = card.top;
              changed = true;
              break; // restart the check with the new breakY
            }
          }
        }

        // Safety: if breakY didn't advance past cursor (card taller than page), force advance
        if (breakY <= cursor) {
          breakY = cursor + pageHeightPx;
        }

        pageBreaks.push(breakY);
        cursor = breakY;
      }

      // Slice canvas into pages based on smart breaks
      const pageImages = [];
      for (let i = 0; i < pageBreaks.length; i++) {
        const sliceY = pageBreaks[i];
        const sliceEnd = i + 1 < pageBreaks.length ? pageBreaks[i + 1] : imgHeight;
        const sliceH = sliceEnd - sliceY;

        const pageCanvas = document.createElement('canvas');
        pageCanvas.width = imgWidth;
        pageCanvas.height = Math.round(pageHeightPx); // full A4 height
        const ctx = pageCanvas.getContext('2d');

        // White background
        ctx.fillStyle = '#ffffff';
        ctx.fillRect(0, 0, pageCanvas.width, pageCanvas.height);

        // Draw the slice
        ctx.drawImage(
          canvas,
          0, Math.round(sliceY), imgWidth, Math.round(sliceH),
          0, 0, imgWidth, Math.round(sliceH)
        );

        pageImages.push(pageCanvas.toDataURL('image/png'));
      }

      setPages(pageImages);

      // Build PDF
      const pdf = new jsPDF({ orientation: 'portrait', unit: 'pt', format: 'a4' });
      for (let i = 0; i < pageImages.length; i++) {
        if (i > 0) pdf.addPage();
        pdf.addImage(pageImages[i], 'PNG', 0, 0, A4_WIDTH_PT, A4_HEIGHT_PT);
      }
      setPdfDoc(pdf);
    } finally {
      grid.classList.remove('pdf-capture-mode');
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (open) {
      setLoading(true);
      setPages([]);
      setPdfDoc(null);
      // Small delay to let the modal render first
      const timer = setTimeout(() => capture(), 100);
      return () => clearTimeout(timer);
    }
  }, [open, capture]);

  const handleDownload = () => {
    if (!pdfDoc) return;
    const filename = `${(dashboardTitle || 'Dashboard').replace(/[^a-zA-Z0-9 _-]/g, '')}.pdf`;
    pdfDoc.save(filename);
  };

  if (!open) return null;

  return (
    <div className="pdf-export-overlay" onClick={onClose}>
      <div className="pdf-export-modal" onClick={(e) => e.stopPropagation()}>
        <div className="pdf-export-header">
          <h3>Export Preview</h3>
          <button className="pdf-close-btn" onClick={onClose}>
            <X size={18} />
          </button>
        </div>

        <div className="pdf-export-body">
          {loading ? (
            <div className="pdf-loading">
              <Loader2 size={28} className="spin" />
              <span>Generating preview...</span>
            </div>
          ) : (
            pages.map((src, i) => (
              <div key={i} className="pdf-page-preview">
                <img src={src} alt={`Page ${i + 1}`} />
                <span className="pdf-page-label">Page {i + 1} of {pages.length}</span>
              </div>
            ))
          )}
        </div>

        <div className="pdf-export-footer">
          <button className="pdf-cancel-btn" onClick={onClose}>Cancel</button>
          <button className="pdf-download-btn" onClick={handleDownload} disabled={loading || !pdfDoc}>
            <Download size={14} />
            Download PDF
          </button>
        </div>
      </div>
    </div>
  );
}
