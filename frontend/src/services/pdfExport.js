import jsPDF from 'jspdf';
import 'jspdf-autotable';
import { formatNumber } from '../utils/format';

export function generatePdfReport({ params, sensors, globalError, inversion }) {
  const doc = new jsPDF();

  doc.setFontSize(18);
  doc.text('Reporte de Localización Sísmica', 14, 22);
  doc.setFontSize(10);
  doc.text(`Fecha: ${new Date().toLocaleString()}`, 14, 30);
  doc.text(`Error Residual Total (E_rr): ${formatNumber(globalError)}`, 14, 36);

  doc.setFontSize(13);
  doc.text('Parámetros Fuente (Iniciales)', 14, 48);
  doc.autoTable({
    startY: 52,
    head: [['x₀', 'y₀', 'z₀', 'A₀', 'α (%)']],
    body: [[params.x0, params.y0, params.z0, params.A0, params.alpha]],
    theme: 'grid',
    headStyles: { fillColor: [56, 189, 248] },
  });

  if (inversion) {
    const y = doc.lastAutoTable.finalY + 10;
    doc.text('Parámetros Estimados (Inversión)', 14, y);
    doc.autoTable({
      startY: y + 4,
      head: [['x₀ calc', 'y₀ calc', 'z₀ calc', 'A₀ calc', 'E_rr final']],
      body: [[
        inversion.estimated.x0.toFixed(2),
        inversion.estimated.y0.toFixed(2),
        inversion.estimated.z0.toFixed(2),
        inversion.estimated.A0.toFixed(2),
        formatNumber(inversion.residualError),
      ]],
      theme: 'grid',
      headStyles: { fillColor: [99, 102, 241] },
    });
  }

  doc.setFontSize(13);
  doc.text('Vector de Observaciones — Todas las Estaciones (Grilla 3×3)', 14, doc.lastAutoTable.finalY + 12);
  doc.autoTable({
    startY: doc.lastAutoTable.finalY + 16,
    head: [['ID', 'Estación', 'X', 'Y', 'Z', 'R (m)', "A' teórica", 'A_zi obs', 'ε']],
    body: sensors.map((s) => [
      s.id,
      s.name,
      s.x.toFixed(1),
      s.y.toFixed(1),
      s.z.toFixed(1),
      s.distance.toFixed(2),
      formatNumber(s.aPred),
      formatNumber(s.lecturaAzi),
      formatNumber(s.epsilon),
    ]),
    theme: 'grid',
    headStyles: { fillColor: [239, 68, 68] },
    styles: { fontSize: 8 },
  });

  doc.setFontSize(9);
  const noteY = doc.lastAutoTable.finalY + 8;
  doc.text('Modelo: A_zi = A₀·e^(-R_i)/R_i + ε_i  |  σ = α·A₀·e^(-R_i)/R_i  |  E_rr = Σ(A_zi - A\'_zi)²', 14, noteY);

  doc.save('Reporte_Simulacion_Sismica.pdf');
}
