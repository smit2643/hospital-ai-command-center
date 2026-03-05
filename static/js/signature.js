(function () {
  const typeField = document.getElementById('id_signature_type');
  const typedBox = document.getElementById('typed-box');
  const drawnBox = document.getElementById('drawn-box');
  const uploadBox = document.getElementById('upload-box');
  const canvas = document.getElementById('sig-canvas');
  const hidden = document.getElementById('drawn_signature_data');
  const clearBtn = document.getElementById('clear-sig');
  const form = document.getElementById('sign-form');

  if (!typeField || !canvas || !hidden || !form) return;

  function refreshMode() {
    const mode = typeField.value;
    typedBox.style.display = mode === 'TYPED' ? 'block' : 'none';
    drawnBox.style.display = mode === 'DRAWN' ? 'block' : 'none';
    if (uploadBox) {
      uploadBox.style.display = mode === 'UPLOADED' ? 'block' : 'none';
    }
  }

  const ctx = canvas.getContext('2d');
  ctx.lineWidth = 2;
  let drawing = false;

  function start(e) {
    drawing = true;
    ctx.beginPath();
    const rect = canvas.getBoundingClientRect();
    const x = (e.touches ? e.touches[0].clientX : e.clientX) - rect.left;
    const y = (e.touches ? e.touches[0].clientY : e.clientY) - rect.top;
    ctx.moveTo(x, y);
  }

  function move(e) {
    if (!drawing) return;
    e.preventDefault();
    const rect = canvas.getBoundingClientRect();
    const x = (e.touches ? e.touches[0].clientX : e.clientX) - rect.left;
    const y = (e.touches ? e.touches[0].clientY : e.clientY) - rect.top;
    ctx.lineTo(x, y);
    ctx.stroke();
  }

  function end() { drawing = false; }

  canvas.addEventListener('mousedown', start);
  canvas.addEventListener('mousemove', move);
  canvas.addEventListener('mouseup', end);
  canvas.addEventListener('mouseleave', end);
  canvas.addEventListener('touchstart', start, { passive: true });
  canvas.addEventListener('touchmove', move, { passive: false });
  canvas.addEventListener('touchend', end);

  clearBtn && clearBtn.addEventListener('click', function () {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    hidden.value = '';
  });

  form.addEventListener('submit', function () {
    if (typeField.value === 'DRAWN') {
      hidden.value = canvas.toDataURL('image/png');
    } else {
      hidden.value = '';
    }
  });

  typeField.addEventListener('change', refreshMode);
  refreshMode();
})();
