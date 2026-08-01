const canvas = document.getElementById('hudCanvas');
const ctx = canvas.getContext('2d');
const subtitleBox = document.getElementById('subtitleBox');

function resizeCanvas() {
  canvas.width = window.innerWidth;
  canvas.height = window.innerHeight;
}

window.addEventListener('resize', resizeCanvas);
resizeCanvas();

// Listen for HUD rendering data from main process
window.godjiAPI.onRenderHUD((hudData) => {
  drawHUD(hudData);
});

function drawHUD(data) {
  // Clear canvas
  ctx.clearRect(0, 0, canvas.width, canvas.height);

  if (!data) return;

  const screenW = canvas.width;
  const screenH = canvas.height;

  // 1. Draw Bounding Boxes
  if (data.bounding_boxes && Array.isArray(data.bounding_boxes)) {
    data.bounding_boxes.forEach(box => {
      // Coordinates normalized 0-1000 or absolute
      const ymin = (box.ymin / 1000) * screenH;
      const xmin = (box.xmin / 1000) * screenW;
      const ymax = (box.ymax / 1000) * screenH;
      const xmax = (box.xmax / 1000) * screenW;
      const w = xmax - xmin;
      const h = ymax - ymin;

      // Draw Box
      ctx.lineWidth = 3;
      ctx.strokeStyle = box.color || '#f97316'; // Orange accent
      ctx.strokeRect(xmin, ymin, w, h);

      // Label background
      ctx.fillStyle = box.color || '#f97316';
      ctx.font = 'bold 16px Segoe UI, sans-serif';
      const textMetrics = ctx.measureText(box.label || 'เป้าหมาย');
      ctx.fillRect(xmin, ymin - 26, textMetrics.width + 16, 26);

      // Label text
      ctx.fillStyle = '#ffffff';
      ctx.fillText(box.label || 'เป้าหมาย', xmin + 8, ymin - 7);
    });
  }

  // 2. Draw Tactical Lead Dots (จุดยิงดัก)
  if (data.lead_dots && Array.isArray(data.lead_dots)) {
    data.lead_dots.forEach(dot => {
      const x = (dot.x / 1000) * screenW;
      const y = (dot.y / 1000) * screenH;

      ctx.beginPath();
      ctx.arc(x, y, 10, 0, 2 * Math.PI);
      ctx.lineWidth = 3;
      ctx.strokeStyle = dot.color || '#3b82f6'; // Blue
      ctx.stroke();

      ctx.beginPath();
      ctx.arc(x, y, 4, 0, 2 * Math.PI);
      ctx.fillStyle = dot.color || '#3b82f6';
      ctx.fill();

      // Lead Dot Label
      ctx.fillStyle = '#ffffff';
      ctx.font = 'bold 15px Segoe UI, sans-serif';
      ctx.fillText(dot.label || 'จุดยิงดัก', x + 16, y + 5);
    });
  }

  // 3. Draw Directional Arrows (ลูกศรทิศทาง)
  if (data.arrows && Array.isArray(data.arrows)) {
    data.arrows.forEach(arrow => {
      const fromX = (arrow.from_x / 1000) * screenW;
      const fromY = (arrow.from_y / 1000) * screenH;
      const toX = (arrow.to_x / 1000) * screenW;
      const toY = (arrow.to_y / 1000) * screenH;

      drawArrow(ctx, fromX, fromY, toX, toY, arrow.label || '');
    });
  }

  // 4. Update Subtitles
  if (data.subtitles) {
    subtitleBox.innerText = `🐉 Godji: ${data.subtitles}`;
    subtitleBox.style.display = 'block';
  } else {
    subtitleBox.style.display = 'none';
  }
}

function drawArrow(ctx, fromx, fromy, tox, toy, label) {
  const headlen = 14;
  const dx = tox - fromx;
  const dy = toy - fromy;
  const angle = Math.atan2(dy, dx);

  ctx.beginPath();
  ctx.moveTo(fromx, fromy);
  ctx.lineTo(tox, toy);
  ctx.lineWidth = 3;
  ctx.strokeStyle = '#38bdf8';
  ctx.stroke();

  ctx.beginPath();
  ctx.moveTo(tox, toy);
  ctx.lineTo(tox - headlen * Math.cos(angle - Math.PI / 6), toy - headlen * Math.sin(angle - Math.PI / 6));
  ctx.lineTo(tox - headlen * Math.cos(angle + Math.PI / 6), toy - headlen * Math.sin(angle + Math.PI / 6));
  ctx.fillStyle = '#38bdf8';
  ctx.fill();

  if (label) {
    ctx.font = 'bold 14px Segoe UI, sans-serif';
    ctx.fillStyle = '#38bdf8';
    ctx.fillText(label, fromx, fromy - 8);
  }
}
