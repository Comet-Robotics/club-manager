(() => {
    const preview = document.getElementById('qr-preview');
    const source = document.querySelector('#qr-source svg');
    const canvas = document.getElementById('qr-canvas');
    const foregroundSelect = document.getElementById('qr-foreground');
    const backgroundSelect = document.getElementById('qr-background');
    const copy = document.getElementById('copyQrImageButton');
    const copyLink = document.getElementById('copySignInLinkButton');
    const download = document.getElementById('downloadQrImageButton');
    const status = document.getElementById('qr-image-status');
    const brand = preview.dataset.brandColor;
    const colors = { black: '#000000', white: '#ffffff', brand, transparent: null };
    const colorContext = document.createElement('canvas').getContext('2d');
    function normalizedColor(value) {
        if (value === null) return null;
        colorContext.fillStyle = value;
        return colorContext.fillStyle;
    }
    let generation = 0;
    let statusTimer;

    function showStatus(message) {
        clearTimeout(statusTimer);
        status.textContent = message;
        statusTimer = setTimeout(() => { status.textContent = ''; }, 2000);
    }

    copyLink.addEventListener('click', async () => {
        const url = copyLink.querySelector('span').textContent.trim();
        try {
            await navigator.clipboard.writeText(url);
        } catch (_) {
            const textArea = document.createElement('textarea');
            textArea.value = url;
            document.body.appendChild(textArea);
            textArea.focus();
            textArea.select();
            try {
                if (!document.execCommand('copy')) throw new Error('Copy failed');
            } catch (_) {
                showStatus('Could not copy the link.');
                return;
            } finally {
                textArea.remove();
            }
        }
        showStatus('Link copied.');
    });

    async function renderPreview() {
        const current = ++generation;
        copy.disabled = download.disabled = true;
        const foreground = colors[foregroundSelect.value];
        const background = colors[backgroundSelect.value];
        const svg = source.cloneNode(true);
        svg.setAttribute('xmlns', 'http://www.w3.org/2000/svg');
        svg.querySelectorAll('path').forEach(path => path.setAttribute('stroke', foreground || '#000000'));
        const extent = Number(svg.getAttribute('width'));
        const size = extent * Math.max(1, Math.floor(1024 / extent));
        svg.setAttribute('width', size);
        svg.setAttribute('height', size);
        const url = URL.createObjectURL(new Blob([new XMLSerializer().serializeToString(svg)], {type: 'image/svg+xml'}));
        try {
            const image = new Image();
            image.src = url;
            await image.decode();
            if (current !== generation) return;
            canvas.width = canvas.height = size;
            const context = canvas.getContext('2d');
            if (background) {
                context.fillStyle = background;
                context.fillRect(0, 0, size, size);
            }
            if (!foreground) context.globalCompositeOperation = 'destination-out';
            context.drawImage(image, 0, 0, size, size);
            context.globalCompositeOperation = 'source-over';
            document.getElementById('qr-source').hidden = true;
            canvas.hidden = false;
            copy.disabled = download.disabled = false;
        } catch (_) {
            if (current === generation) showStatus('Could not generate the image. Try another browser.');
        } finally {
            URL.revokeObjectURL(url);
        }
    }

    function pngBlob() {
        return new Promise((resolve, reject) => canvas.toBlob(blob => blob ? resolve(blob) : reject(new Error('PNG generation failed')), 'image/png'));
    }

    copy.addEventListener('click', async () => {
        try {
            if (!navigator.clipboard?.write || !window.ClipboardItem) throw new Error('Image clipboard unavailable');
            // Construct the ClipboardItem during the click so browsers retain user activation.
            await navigator.clipboard.write([new ClipboardItem({'image/png': pngBlob()})]);
            showStatus('Image copied. Paste it into your slide.');
        } catch (_) {
            showStatus('Could not copy the image. Use Download PNG instead.');
        }
    });

    download.addEventListener('click', async () => {
        try {
            const url = URL.createObjectURL(await pngBlob());
            const link = document.createElement('a');
            link.href = url;
            link.download = 'event-sign-in-qr.png';
            link.click();
            setTimeout(() => URL.revokeObjectURL(url), 1000);
            showStatus('PNG downloaded.');
        } catch (_) {
            showStatus('Could not download the image. Please try again.');
        }
    });

    function updateSelection() {
        for (const option of foregroundSelect.options) {
            option.disabled = normalizedColor(colors[option.value]) === normalizedColor(colors[backgroundSelect.value]);
        }
        for (const option of backgroundSelect.options) {
            option.disabled = normalizedColor(colors[option.value]) === normalizedColor(colors[foregroundSelect.value]);
        }
        renderPreview();
    }
    foregroundSelect.addEventListener('change', updateSelection);
    backgroundSelect.addEventListener('change', updateSelection);
    updateSelection();
})();
