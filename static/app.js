const urlInput = document.getElementById("urlInput");
const downloadForm = document.getElementById("downloadForm");
const previewMeta = document.getElementById("previewMeta");
const previewThumb = document.getElementById("previewThumb");
const previewTitle = document.getElementById("previewTitle");
const previewChannel = document.getElementById("previewChannel");
const previewDuration = document.getElementById("previewDuration");
const modeRadios = document.querySelectorAll("input[name='mode']");
const qualityField = document.getElementById("qualityField");
const qualityHint = document.getElementById("qualityHint");
const qualitySelect = document.getElementById("qualitySelect");
const videoQualityField = document.getElementById("videoQualityField");
const videoQualityHint = document.getElementById("videoQualityHint");
const videoQualitySelect = document.getElementById("videoQualitySelect");
const statusMessage = document.getElementById("statusMessage");
const urlFeedback = document.getElementById("urlFeedback");
const downloadButton = document.getElementById("downloadButton");
const btnSpinner = document.getElementById("btnSpinner");
const btnText = document.getElementById("btnText");

let lastPreviewId = null;
let previewTimeout = null;

const decodeFileName = (value) => {
  try {
    return decodeURIComponent(value);
  } catch {
    return value;
  }
};

const getDownloadFileName = (disposition, fallbackMode) => {
  if (disposition) {
    const filenameStarMatch = disposition.match(/filename\*=UTF-8''([^;]+)/i);
    if (filenameStarMatch?.[1]) {
      return decodeFileName(filenameStarMatch[1]);
    }

    const filenameMatch = disposition.match(/filename="?([^";]+)"?/i);
    if (filenameMatch?.[1]) {
      return decodeFileName(filenameMatch[1]);
    }
  }

  return fallbackMode === "mp3" ? "download.mp3" : "download.mp4";
};

const extractYouTubeId = (url) => {
  if (!url) return null;

  const patterns = [
    /v=([^&]+)/,
    /youtu\.be\/([^?]+)/,
    /youtube\.com\/shorts\/([^?]+)/,
    /youtube\.com\/embed\/([^?]+)/,
  ];

  for (const pattern of patterns) {
    const match = url.match(pattern);
    if (match && match[1]) {
      return match[1];
    }
  }

  return null;
};

const setStatus = (message, type = "neutral") => {
  statusMessage.textContent = message;
  statusMessage.dataset.type = type;
  statusMessage.classList.toggle("show", Boolean(message));
};

const setLoading = (isLoading) => {
  const hasValidUrl = Boolean(extractYouTubeId(urlInput.value.trim()));
  downloadButton.disabled = isLoading || !hasValidUrl;
  btnSpinner.classList.toggle("show", isLoading);
  btnText.textContent = isLoading ? "Processando..." : "Baixar";
};

const resetPreview = () => {
  previewMeta.classList.remove("show");
  previewTitle.textContent = "Título do vídeo";
  previewChannel.textContent = "Canal";
  previewDuration.textContent = "Duração";
  previewThumb.removeAttribute("src");
};

const applyPreview = (videoId, data) => {
  previewTitle.textContent = data.title || "Sem título";
  previewChannel.textContent = data.channel || "Canal desconhecido";
  previewDuration.textContent = `Duração: ${data.duration || "--:--"}`;
  if (data.thumbnail) {
    previewThumb.src = data.thumbnail;
  }
  previewMeta.classList.add("show");
};

const updatePreview = () => {
  const value = urlInput.value.trim();
  const videoId = extractYouTubeId(value);

  if (!videoId) {
    resetPreview();
    setStatus("");
    urlFeedback.textContent = "Cole uma URL do YouTube para habilitar o download.";
    downloadButton.disabled = true;
    lastPreviewId = null;
    return;
  }

  urlFeedback.textContent = "Link válido detectado.";
  downloadButton.disabled = false;

  if (videoId === lastPreviewId) {
    return;
  }

  lastPreviewId = videoId;
  setStatus("Carregando prévia...", "neutral");

  fetch(`/api/preview?url=${encodeURIComponent(value)}`)
    .then(async (response) => {
      if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        throw new Error(payload.error || "Falha ao obter prévia.");
      }
      return response.json();
    })
    .then((data) => {
      if (lastPreviewId !== videoId) return;
      applyPreview(videoId, data);
      setStatus("Prévia carregada. Escolha o formato e baixe.", "success");
    })
    .catch((error) => {
      if (lastPreviewId !== videoId) return;
      resetPreview();
      setStatus(error.message, "error");
      downloadButton.disabled = true;
    });
};

const updateQualityState = () => {
  const mode = document.querySelector("input[name='mode']:checked").value;
  const isMp4 = mode === "mp4";

  qualityField.classList.toggle("hidden", isMp4);
  qualityField.classList.toggle("disabled", isMp4);
  qualityHint.style.opacity = isMp4 ? "0" : "1";
  qualitySelect.disabled = isMp4;

  videoQualityField.classList.toggle("hidden", !isMp4);
  videoQualityField.classList.toggle("disabled", !isMp4);
  videoQualityHint.style.opacity = isMp4 ? "1" : "0";
  videoQualitySelect.disabled = !isMp4;
};

const debouncePreview = () => {
  clearTimeout(previewTimeout);
  previewTimeout = setTimeout(updatePreview, 280);
};

downloadForm.addEventListener("submit", async (event) => {
  event.preventDefault();

  const videoId = extractYouTubeId(urlInput.value.trim());
  if (!videoId) {
    setStatus("Informe uma URL válida do YouTube.", "error");
    return;
  }

  setLoading(true);
  setStatus("Iniciando download...", "neutral");

  try {
    const formData = new FormData(downloadForm);
    const response = await fetch("/api/download", {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      const payload = await response.json().catch(() => ({}));
      throw new Error(payload.error || "Não foi possível concluir o download.");
    }

    const blob = await response.blob();
    const disposition = response.headers.get("Content-Disposition") || "";
    const mode = formData.get("mode") === "mp4" ? "mp4" : "mp3";
    const fileName = getDownloadFileName(disposition, mode);

    const blobUrl = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = blobUrl;
    anchor.download = fileName;
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    URL.revokeObjectURL(blobUrl);

    setStatus("Download concluído com sucesso.", "success");
  } catch (error) {
    setStatus(error.message || "Erro inesperado no download.", "error");
  } finally {
    setLoading(false);
  }
});

urlInput.addEventListener("input", debouncePreview);
modeRadios.forEach((radio) => radio.addEventListener("change", updateQualityState));

updateQualityState();
resetPreview();
