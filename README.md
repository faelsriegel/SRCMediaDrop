# 🎵 SRC MediaDrop

Downloader de **YouTube para MP3 ou MP4**, feito em Python, com duas interfaces:
- **Web moderna (FastAPI)** com prévia do vídeo e UX otimizada
- **Terminal (CLI)** para fluxo rápido
- **Launcher Desktop (sem terminal)** para usuários leigos

O projeto utiliza **yt-dlp** e **FFmpeg** para baixar e converter mídia com qualidade.

---

## 🚀 Funcionalidades

- Baixa áudio e vídeo de links do YouTube
- Converte para **MP3** (128/192/256 kbps)
- Baixa em **MP4** (melhor qualidade disponível)
- Prévia embutida do vídeo na interface web
- Metadados na prévia (título, canal, duração, thumbnail)
- Validação de URL e feedback visual de estados (loading/sucesso/erro)
- Escolha de qualidade:
  - 128 kbps (baixa)
  - 192 kbps (recomendada)
  - 256 kbps (alta)
- Download direto para a pasta de downloads do projeto
- Interface moderna via navegador
- Interface simples via terminal
- Sem anúncios, sem limites e sem dependência de sites externos

---

## 🛠️ Tecnologias utilizadas

- **Python 3**
- **yt-dlp**
- **FFmpeg**
- **FastAPI + Uvicorn + Jinja2**
- **Tkinter (launcher desktop)**
- **Pystray + Pillow (ícone de bandeja)**

---

## 📂 Estrutura do projeto

```

youtube-mp3-converter/
│
├── main.py
├── requirements.txt
├── downloads/
└── ffmpeg/
   ├── ffmpeg.exe
   └── ffprobe.exe

````

---

## 📦 Requisitos

- Python 3.9+
- FFmpeg
   - **macOS**: `brew install ffmpeg`
   - **Windows**: usar `ffmpeg.exe` em `ffmpeg/` (como já está no projeto)

---

## ⚙️ Instalação

1. Clone o repositório:
   ```bash
   git clone https://github.com/GutoVieoli/Youtube_MP3_Converter.git
    ```

2. Entre na pasta do projeto:

   ```bash
   cd Youtube_MP3_Converter
   ```

3. Instale as dependências:

   ```bash
   pip install -r requirements.txt
   ```

> O `requirements.txt` contém apenas a versão do **yt-dlp**, mantendo o projeto simples e limpo.

---

## ▶️ Como usar (Web - recomendado)

Execute:

```bash
uvicorn web_app:app --reload
```

Abra:

```text
http://127.0.0.1:8000
```

Fluxo:
1. Cole a URL do YouTube
2. Veja a prévia automática
3. Escolha MP3 ou MP4
4. Clique em baixar

---

## 🧩 Como usar (Sem terminal - Launcher Desktop)

Execute:

```bash
python launcher_gui.py
```

Depois, no app:
1. Clique em **Iniciar**
2. Clique em **Abrir Página**
3. Use o downloader normalmente no navegador

Recursos do launcher profissional:
- **Iniciar com o sistema** (Windows/macOS)
- **Minimizar para bandeja** ao fechar
- **Detecção de servidor já ativo** (evita erro de porta)
- **Healthcheck interno** para monitorar disponibilidade local

---

## 📦 Gerar executável (para leigos)

Os scripts abaixo já fazem build **release** com ícone customizado automático.
Também aplicam metadados de versão para distribuição mais profissional.

### Windows (.exe)

No Prompt/PowerShell, dentro da pasta do projeto:

```bash
build_windows_exe.bat
```

Saída:

```text
dist\SRCMediaDrop.exe
```

Ícone gerado em:

```text
build\icons\app_icon.ico
build\windows_version.txt
```

### macOS (.app)

No Terminal:

```bash
chmod +x build_macos_app.sh
./build_macos_app.sh
```

Saída:

```text
dist/SRCMediaDrop.app
```

Ícones gerados em:

```text
build/icons/app_icon.png
build/icons/app_icon.icns (quando disponível)
```

Configuração central de app (nome, versão, etc.):

```text
app_meta.py
```

---

## 🖥️ Como usar (CLI)

Execute o programa com:

```bash
python main.py
```

### Passo a passo:

1. Cole a URL do vídeo do YouTube
2. Escolha a qualidade do áudio:

   * A → 128 kbps
   * B → 192 kbps
   * C → 256 kbps
3. O arquivo será baixado para a pasta `downloads`


---

## ⚠️ Observações

* O projeto é destinado **apenas para uso pessoal**
* Certifique-se de respeitar os **termos do YouTube** e os **direitos autorais**
* O nome do arquivo é baseado no título do vídeo

---

## 🧠 Motivação

Este projeto foi criado para:

* Evitar sites online cheios de propagandas
* Ter mais controle sobre qualidade e destino dos arquivos
* Aprender e praticar automação com Python

---

## 📄 Licença

Este projeto é de uso livre para fins educacionais e pessoais.
