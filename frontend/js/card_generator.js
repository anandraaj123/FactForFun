/**
 * Fact₹1 Dynamic Social Card Canvas Generator
 * Minimalist Monochrome (Black, White & Grey)
 */

class FactCardGenerator {
  constructor(canvasElement) {
    this.canvas = canvasElement;
    this.ctx = canvasElement.getContext('2d');
    this.width = 1080;
    this.height = 1080;
    this.canvas.width = this.width;
    this.canvas.height = this.height;
  }

  wrapText(text, maxWidth, font, fontSize) {
    this.ctx.font = `${fontSize}px ${font}`;
    const words = text.split(' ');
    const lines = [];
    let currentLine = words[0];

    for (let i = 1; i < words.length; i++) {
      const word = words[i];
      const width = this.ctx.measureText(currentLine + ' ' + word).width;
      if (width < maxWidth) {
        currentLine += ' ' + word;
      } else {
        lines.push(currentLine);
        currentLine = word;
      }
    }
    lines.push(currentLine);
    return lines;
  }

  render(factData) {
    const ctx = this.ctx;
    const w = this.width;
    const h = this.height;

    // 1. Pure Dark Background
    ctx.fillStyle = '#000000';
    ctx.fillRect(0, 0, w, h);

    // 2. Subtle Radial Light
    const glow = ctx.createRadialGradient(w / 2, 350, 40, w / 2, 350, 500);
    glow.addColorStop(0, 'rgba(255, 255, 255, 0.05)');
    glow.addColorStop(1, 'rgba(0, 0, 0, 0)');
    ctx.fillStyle = glow;
    ctx.fillRect(0, 0, w, h);

    // 3. Outer Decorative Border
    ctx.strokeStyle = '#27272a';
    ctx.lineWidth = 3;
    ctx.strokeRect(40, 40, w - 80, h - 80);

    // Inner Card
    ctx.fillStyle = '#09090b';
    ctx.beginPath();
    ctx.roundRect(80, 80, w - 160, h - 160, 24);
    ctx.fill();
    ctx.strokeStyle = '#3f3f46';
    ctx.lineWidth = 1.5;
    ctx.stroke();

    // 4. Header: FACT₹1 • CATEGORY
    const category = (factData.category || 'Curiosity').toUpperCase();
    ctx.fillStyle = '#a1a1aa';
    ctx.font = '700 24px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
    ctx.textAlign = 'left';
    ctx.fillText(`FACT₹1  •  ${category}`, 130, 165);

    // Badge
    ctx.fillStyle = '#ffffff';
    ctx.beginPath();
    ctx.roundRect(w - 240, 135, 110, 40, 20);
    ctx.fill();
    ctx.fillStyle = '#000000';
    ctx.font = '800 22px -apple-system, BlinkMacSystemFont, sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText('₹1 FACT', w - 185, 163);

    // 5. Emoji & Header
    ctx.textAlign = 'left';
    ctx.font = '64px sans-serif';
    ctx.fillText('🤯', 130, 270);

    ctx.fillStyle = '#71717a';
    ctx.font = '700 26px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
    ctx.fillText('DID YOU KNOW?', 220, 255);

    // 6. Fact Text
    const factText = factData.fact_text || factData.fact || factData.title;
    const factLines = this.wrapText(factText, w - 260, '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif', 46);
    
    ctx.fillStyle = '#ffffff';
    ctx.font = '800 46px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
    let currentY = 360;
    factLines.forEach((line) => {
      ctx.fillText(line, 130, currentY);
      currentY += 60;
    });

    currentY += 20;

    // 7. Explanation
    if (factData.explanation) {
      const expLines = this.wrapText(factData.explanation, w - 290, '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif', 28);
      
      ctx.fillStyle = '#52525b';
      ctx.fillRect(130, currentY - 20, 4, (expLines.length * 40) + 10);

      ctx.fillStyle = '#a1a1aa';
      ctx.font = '500 28px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
      expLines.forEach((line) => {
        ctx.fillText(line, 155, currentY + 10);
        currentY += 40;
      });
    }

    // 8. Footer
    const footerY = h - 140;
    
    ctx.fillStyle = '#71717a';
    ctx.font = '600 22px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
    const sourceText = `Verified Source: ${factData.source_name || 'Official Institution Archive'}`;
    ctx.fillText(sourceText, 130, footerY);

    ctx.textAlign = 'right';
    ctx.fillStyle = '#ffffff';
    ctx.font = '800 24px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
    ctx.fillText('( Fact ₹1 ) → fact1.in', w - 130, footerY);
  }

  toDataURL() {
    return this.canvas.toDataURL('image/png');
  }

  download(filename = 'fact1-curiosity.png') {
    const link = document.createElement('a');
    link.download = filename;
    link.href = this.toDataURL();
    link.click();
  }
}

window.FactCardGenerator = FactCardGenerator;
