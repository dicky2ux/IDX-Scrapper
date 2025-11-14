# IDX-Scrapper-Github

# IDX Scraper — Panduan Lengkap untuk Pemula (dari VSCode sampai CSV)

Alat ini mengekspor pengumuman dari situs Bursa Efek Indonesia (IDX). Hasil export berisi tiga kolom utama:

- Kode_Emiten
- Judul_Pengumuman
- Tanggal_Pengumuman

Panduan ini ditulis khusus untuk pengguna awam: langkah demi langkah mulai dari menginstal editor (Visual Studio Code), memasang Python, membuka proyek, sampai menjalankan program dan mendapatkan file CSV yang bisa dibuka di Excel/LibreOffice.

Jika Anda kurang paham istilah teknis, ikuti perintah satu per satu.

---

Ringkasnya, yang akan kita lakukan:

1. Install Visual Studio Code (VSCode) — editor yang memudahkan.
2. Install Python 3 (jika belum ada).
3. Buka proyek di VSCode dan jalankan terminal di dalamnya.
4. Buat virtual environment (isolasi paket) dan pasang dependensi.
5. Install Playwright browser binaries (satu kali per mesin).
6. Buat file `.env` dengan helper interaktif (`idx env`).
7. Jalankan login interaktif sekali untuk menyelesaikan challenge Cloudflare.
8. Jalankan scraping headless untuk menghasilkan `out.csv`.
9. Buka CSV hasil scraping di Excel/LibreOffice.

---

## 0. Siapkan info dasar

Sebelum mulai, siapkan:

- Komputer dengan akses internet.
- Akun email yang terdaftar di IDX (untuk login jika perlu).
- Izin untuk menginstal perangkat lunak (pada beberapa PC kantor, Anda perlu hak admin).

Catatan: petunjuk di bawah mencakup macOS, Windows, dan Linux (Ubuntu/Debian).

---

## 1. Instal Visual Studio Code (VSCode)

VSCode adalah editor kode tetapi juga berguna untuk menjalankan Terminal dan melihat file.

- Untuk macOS / Windows: buka https://code.visualstudio.com/ dan unduh installer. Jalankan installer.

- Untuk Ubuntu/Debian: jalankan:
```bash
# contoh untuk Ubuntu/Debian
sudo apt update
sudo apt install -y wget apt-transport-https software-properties-common
wget -qO- https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor > microsoft.gpg
sudo install -o root -g root -m 644 microsoft.gpg /usr/share/keyrings/
sudo sh -c 'echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/microsoft.gpg] https://packages.microsoft.com/repos/code stable main" > /etc/apt/sources.list.d/vscode.list'
sudo apt update
sudo apt install -y code
```

Setelah terinstall, buka VSCode.

---

## 2. Install Python 3 (jika belum ada)

Periksa versi Python di Terminal/PowerShell di dalam VSCode atau di sistem Anda:
- macOS / Linux:
```bash
python3 --version
```

- Windows (PowerShell):
```powershell
python --version
```

Jika muncul versi 3.x, lanjut ke langkah berikutnya. Jika tidak, ikuti langkah sesuai OS:

- macOS (via Homebrew):
-- Tekan tombol "Ctrl + ` (backtick)" di VSCode untuk membuka terminal, lalu jalankan:
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"  # jika belum punya Homebrew
brew install python # jika belum ada Python setelah install Homebrew
```

- Ubuntu / Debian (Linux):
-- Tekan tombol "Ctrl + ` (backtick)" di VSCode untuk membuka terminal, lalu jalankan:
```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip
```

- Windows:
1. Buka https://www.python.org/downloads/windows/ dan unduh installer Python 3.x.
2. Jalankan installer, pastikan mencentang "Add Python to PATH" lalu klik Install.

Verifikasi:

- macOS / Linux:
```bash
python3 --version
pip3 --version
```
- Windows (PowerShell):
```powershell
python --version
```

---

## 3. Buka proyek di VSCode dan gunakan Terminal bawaan

1. Buka VSCode.
2. Pilih menu File → Open Folder... lalu pilih folder proyek (`IDX-Scrapper` atau folder tempat Anda menyimpan repository).
3. Buka Terminal di VSCode: View → Terminal. Terminal default biasanya Bash (macOS/Linux) atau PowerShell (Windows).

Semua perintah di panduan berikut dijalankan di terminal ini.

---

## 4. Siapkan virtual environment (direkomendasikan)

Virtual environment memastikan paket Python proyek tidak bercampur dengan paket sistem.

Di terminal (pastikan sudah berada di folder proyek):

```bash
# buat virtualenv
python3 -m venv .venv

# aktifkan venv (macOS/Linux)
source .venv/bin/activate

# Windows PowerShell:
# .\.venv\Scripts\Activate.ps1
```

Setelah aktif, prompt Terminal biasanya berubah menunjukkan `.venv`.

---

## 5. Pasang dependensi Python dan Playwright

Masih di terminal (virtualenv aktif):

```bash
pip install --upgrade pip
pip install -r requirements.txt

# Install browser binaries Playwright (wajib untuk mode Playwright)
python -m playwright install
```

---

## 6. Buat file `.env` (helper interaktif)

Untuk menyimpan email/password sementara secara lokal, gunakan helper interaktif:

```bash
python3 scripts/create_env.py
# atau via helper executable jika Anda sudah meng-install: ./idx env
```

Helper akan menanyakan email, password, dan opsi proxy. Ia menulis file `.env` di folder proyek dan memberi peringatan untuk tidak commit file `.env` ini ke Git.

---

## 7. Login interaktif (satu kali, di mesin dengan GUI)

Beberapa proteksi situs (Cloudflare) memerlukan interaksi manusia pada kali pertama. Lakukan langkah ini di mesin dengan browser GUI:

```bash
python3 export_idx_keywords_csv.py --output tmp_after_login.csv --login --login-email you@example.com --login-password "PASSWORD"
# atau via helper
./idx login --email you@example.com --password "PASSWORD" --save-credentials
```

Perhatikan output di terminal. Jika login berhasil, skrip akan menyimpan Playwright `storage_state` di lokasi default:

```
~/.config/idx-scraper/playwright_storage_state.json
```

Setelah `storage_state` tersimpan, Anda dapat menjalankan scraping secara otomatis (non-interaktif) di mesin yang sama.

---

## 8. Menjalankan scraping otomatis (headless) dan mendapatkan CSV

Jika `storage_state` sudah ada, jalankan:

```bash
python3 export_idx_keywords_csv.py --output out.csv --automated-playwright --headless
# atau via helper
./idx run --output out.csv --headless
```

Perintah ini akan menulis file `out.csv` di folder kerja (atau path yang Anda tentukan dengan `--output`).

Untuk memeriksa hasil:

- Di Windows/macOS: buka `out.csv` dengan Excel.
- Di Linux: buka dengan LibreOffice Calc atau gunakan `cat out.csv | head` untuk melihat baris pertama di terminal.

Contoh cek cepat di terminal:

```bash
head -n 10 out.csv
```

CSV menggunakan pemisah `;` (titik koma). Jika Excel menampilkan semua data dalam satu kolom, buka Excel → Data → From Text/CSV lalu pilih delimiter `;`.

---

## 9. Jika Anda mau menjalankan terjadwal (cron) atau di GitHub Actions

- Cron: pastikan `storage_state` tersedia di mesin tersebut (simpan di `~/.config/idx-scraper/playwright_storage_state.json`), lalu tambahkan entry crontab yang memanggil perintah headless.
- GitHub Actions: contoh workflow `scrape.yml` sudah ditambahkan. Simpan `IDX_AUTH_EMAIL` dan `IDX_AUTH_PASSWORD` di Secrets repo. Perhatikan bahwa Cloudflare kadang memerlukan interaksi manusia; CI bisa gagal jika challenge muncul.

Contoh command-line / snippet terminal:

- Buat storage state (jalankan sekali di mesin dengan GUI):
```bash
# jalankan login interaktif sekali untuk menyelesaikan Cloudflare challenge
python3 export_idx_keywords_csv.py --output tmp_after_login.csv --login --login-email you@example.com --login-password "PASSWORD"
# setelah sukses, file storage state akan tersimpan di:
# ~/.config/idx-scraper/playwright_storage_state.json
```

- Contoh entry crontab (jalankan setiap hari jam 02:00):
```cron
# buka crontab: crontab -e
0 2 * * * cd /path/to/idx-scraper && /usr/bin/python3 export_idx_keywords_csv.py --output /path/to/output/idx_$(date +\%Y\%m\%d).csv --automated-playwright --headless
```

- Baris terminal untuk manual run headless:
```bash
cd /path/to/idx-scraper
# jalankan scraping headless, hasil ke out.csv
python3 export_idx_keywords_csv.py --output out.csv --automated-playwright --headless
# atau via helper jika sudah terinstall
./idx run --output out.csv --headless
```

- Contoh potongan GitHub Actions (step yang menjalankan scraping):
```yaml
- name: Install deps and browsers
    run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        python -m playwright install

- name: Run headless scrape
    env:
        IDX_AUTH_EMAIL: ${{ secrets.IDX_AUTH_EMAIL }}
        IDX_AUTH_PASSWORD: ${{ secrets.IDX_AUTH_PASSWORD }}
    run: |
        python3 export_idx_keywords_csv.py --output out.csv --automated-playwright --headless --persist-login
```

Tips singkat:
- Pastikan path `python3` pada crontab sesuai lokasi Python di mesin cron.
- Jika runner/host berbeda dari mesin yang Anda gunakan untuk login interaktif, salin `~/.config/idx-scraper/playwright_storage_state.json` ke user yang menjalankan cron/CI atau ulangi login interaktif di mesin tersebut.
- Simpan file output (`out.csv`) ke lokasi yang mudah diambil (artifact di CI atau direktori yang dipantau).

---

## 10. Troubleshooting untuk pemula

- "Command not found" saat menjalankan `python3` atau `pip`:
  - Anda belum menginstal Python atau PATH belum diatur. Ikuti langkah instalasi Python di bagian atas.

- Playwright meminta install atau gagal menemukan browser:
  - Jalankan `python -m playwright install` dan coba lagi.

- Hasil CSV kosong atau berisi HTML:
  - Kemungkinan Cloudflare menolak permintaan headless. Jalankan login interaktif di mesin dengan GUI untuk menyelesaikan challenge "I'm not a Robot", lalu ulangi headless.

- Excel menampilkan semua data dalam satu kolom:
  - Saat membuka, pastikan memilih delimiter `;` (titik koma).

Jika Anda menemui error, salin pesan error (atau screenshot) dan cobalah gunakan ChatGPT atau Gemini untuk mendapat solusi sementara.

---

## Ringkasan singkat (apa yang perlu dilakukan)

1. Install Python (instruksi di bawah untuk macOS / Windows / Linux).
2. Buat virtual environment (direkomendasikan), aktifkan.
3. Pasang dependensi Python dari `requirements.txt`.
4. Install browser untuk Playwright (satu kali per mesin): `python -m playwright install`.
5. Buat file `.env` dengan kredensial (bisa menggunakan helper interaktif `idx env`).
6. Jalankan login interaktif sekali untuk menyelesaikan Cloudflare challenge.
7. Setelah login tersimpan (storage state), jalankan mode headless untuk scraping otomatis.

---

## 1. Cara menginstall Python (pemula)

Pilih sistem operasi Anda dan ikuti langkah singkat berikut.

- macOS (direkomendasikan menggunakan Homebrew):

  1. Jika belum punya Homebrew, buka Terminal dan jalankan:

     ```bash
     /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
     ```

  2. Install Python 3:

     ```bash
     brew install python
     ```

  3. Verifikasi:

     ```bash
     python3 --version
     pip3 --version
     ```

- Ubuntu / Debian (Linux):

  ```bash
  sudo apt update
  sudo apt install -y python3 python3-venv python3-pip
  python3 --version
  ```

- Windows:

  1. Buka https://www.python.org/downloads/windows/ dan unduh installer Python 3.x.
  2. Jalankan installer dan centang opsi "Add Python to PATH" sebelum Install.
  3. Buka PowerShell dan verifikasi:

     ```powershell
     python --version
     pip --version
     ```

---

## 2. Setup proyek (langkah demi langkah, pemula)

Buka Terminal (macOS/Linux) atau PowerShell (Windows), lalu jalankan:

```bash
git clone <repo-url> idx-scraper
cd idx-scraper
# Buat virtualenv dan aktifkan (direkomendasikan)
python3 -m venv .venv
source .venv/bin/activate   # macOS/Linux
# .venv\Scripts\Activate.ps1  # PowerShell (Windows) — gunakan dengan PowerShell

# Upgrade pip dan install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Install Playwright browser binaries (wajib untuk mode Playwright)
python -m playwright install
```

Catatan Windows: untuk mengaktifkan venv di PowerShell, jalankan:

```powershell
. .\.venv\Scripts\Activate.ps1
```

---

## 3. Menyimpan kredensial dengan aman

Aplikasi membutuhkan kredensial agar bisa melakukan login pada situs IDX. Pilihan aman:

- Gunakan helper interaktif untuk membuat `.env` file lokal (direkomendasikan untuk penggunaan lokal):

  ```bash
  python3 scripts/create_env.py
  # atau via helper: ./idx env
  ```

  Helper akan menulis file `.env` di folder proyek. File ini tidak boleh dikomit ke Git — sudah ada di `.gitignore`.

- Atau set environment variables langsung (bagus untuk CI):

  - IDX_AUTH_EMAIL
  - IDX_AUTH_PASSWORD
  - (opsional) IDX_AUTH_TOKEN
  - (opsional) IDX_PROXY

- Opsional: simpan di keyring OS (tool mendukung `--save-credentials` saat login interaktif).

---

## 4. Login interaktif — selesai sekali untuk menyimpan sesi

Beberapa proteksi (Cloudflare) mengharuskan interaksi manusia saat pertama kali. Jalankan perintah ini di mesin dengan browser GUI:

```bash
python3 export_idx_keywords_csv.py --output tmp_after_login.csv --login --login-email you@example.com --login-password "PASSWORD"
# atau via helper
./idx login --email you@example.com --password "PASSWORD" --save-credentials
```

Setelah login berhasil, Playwright menyimpan `storage_state` (session cookies + localStorage) ke lokasi default: `~/.config/idx-scraper/playwright_storage_state.json`. Lokasi ini memungkinkan Anda menjalankan scraping non-interaktif di kemudian hari.

---

## 5. Menjalankan scraping headless (otomatis)

Jika storage state sudah ada (setelah login interaktif), jalankan scraping secara non-interaktif (headless):

```bash
python3 export_idx_keywords_csv.py --output out.csv --automated-playwright --headless
# atau via helper
./idx run --output out.csv --headless
```

Jika Anda ingin workflow CI membuat storage state (sekali) dan menyimpannya (risikonya disebut di bawah), gunakan `--persist-login` bersama Secrets.

---

## 6. Contoh cron (menjalankan setiap hari jam 02:00 lokal)

Tambahkan baris berikut ke crontab (sesuaikan path Python dan folder proyek):

```cron
0 2 * * * cd /path/to/idx-scraper && /usr/bin/python3 export_idx_keywords_csv.py --output /path/to/output/idx_$(date +\%Y\%m\%d).csv --automated-playwright --headless
```

Pastikan storage state sudah dibuat di mesin itu terlebih dahulu (lihat langkah Login interaktif).

---

## 7. Contoh GitHub Actions (cara aman menggunakan Secrets)

Saya sudah menambahkan contoh workflow `scrape.yml` yang bisa Anda sesuaikan. Inti aman yang harus Anda lakukan:

1. Simpan `IDX_AUTH_EMAIL` dan `IDX_AUTH_PASSWORD` di GitHub → Settings → Secrets.
2. Workflow akan men-download browser Playwright, install dependensi, lalu menjalankan:

   ```bash
   python3 export_idx_keywords_csv.py --output out.csv --automated-playwright --headless --persist-login
   ```

3. Workflow meng-upload `out.csv` sebagai artifact job.

Catatan keamanan penting: runner CI masih bisa ditantang oleh Cloudflare yang memerlukan interaksi manusia. Jika terjadi, Anda perlu mempertimbangkan menjalankan login interaktif di mesin yang dapat memenuhi challenge, atau menggunakan solusi berbayar/terpercaya yang menangani bot protection.

---

## 8. Troubleshooting singkat (pemula)

- Playwright tidak ditemukan / browser belum ter-install:

  - Jalankan `python -m playwright install` di mesin tersebut.

- Headless run mengembalikan HTML bukan CSV (indikasi Cloudflare/challenge):

  - Jalankan login interaktif di mesin dengan GUI (`--login` atau `--interactive`) dan ulangi headless setelah storage state tersimpan.

- Saya tidak tahu cara memasang Python / pip / virtualenv di OS saya:

  - Buka bagian "Cara menginstall Python" di atas atau beri tahu OS Anda — saya bantu langkah demi langkah.
- Jangan commit file sensitif ( `.env`, storage state, cookies ).

---

## 9. Untuk kontributor / pengembang

- Buat virtualenv, jalankan tests (jika ada), dan buat PR untuk fitur baru.
- Untuk membuat paket Python yang bisa dipasang: `pip install .` di root repo (ada `pyproject.toml`).

---

Alat ini mengekspor pengumuman dari situs IDX (kolom: Kode_Emiten, Judul_Pengumuman, Tanggal_Pengumuman). README ini berisi panduan langkah-demi-langkah untuk menginstal, mengonfigurasi kredensial, melakukan login interaktif, menjalankan scraping secara headless, serta contoh penggunaan di cron dan GitHub Actions.

## Ringkasan singkat

- Pasang dependensi Python dan Playwright.
- Buat `.env` atau simpan kredensial di environment/keyring.
- Jalankan login interaktif sekali untuk menyelesaikan challenge Cloudflare.
- Setelah itu, jalankan mode headless (`--automated-playwright --headless`) untuk scraping non-interaktif.

---

## Panduan Langkah-demi-Langkah

Dokumentasi ini menjelaskan cara men-setup dan menjalankan alat IDX Scraper secara lokal, lewat cron, dan contoh penggunaan di CI (GitHub Actions). Semua contoh menggunakan shell Bash.

Catatan singkat: tool ini mengekspor kolom `Kode_Emiten`, `Judul_Pengumuman`, dan `Tanggal_Pengumuman` untuk kata kunci bawaan. Karena situs IDX memiliki proteksi (Cloudflare/JS), alat ini memakai Playwright untuk sesi yang memerlukan browser dan juga menyediakan jalur non-interaktif bila Anda sudah menyimpan Playwright storage state.

### 1) Clone repository

```bash
git clone <repo-url> idx-scraper
cd idx-scraper
```

### 2) Buat virtual environment (direkomendasikan)

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3) Pasang dependensi Python

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4) Install browser Playwright (wajib untuk mode Playwright)

Playwright membutuhkan browser binaries. Jalankan sekali di mesin Anda (akan mengunduh ~100+ MB):

```bash
python -m playwright install
```

### 5) Siapkan kredensial pengguna (aman)

Anda punya beberapa pilihan untuk menyimpan kredensial dan token:

- Gunakan file `.env` lokal (direkomendasikan untuk pengembangan lokal). Ada helper interaktif `scripts/create_env.py` untuk membuat `.env` dengan aman.
- Gunakan environment variables langsung: `IDX_AUTH_EMAIL`, `IDX_AUTH_PASSWORD`, `IDX_AUTH_TOKEN`, `IDX_PROXY`.
- Simpan di OS keyring (opsional): gunakan `--save-credentials` saat menjalankan `--login`.

Contoh membuat `.env` interaktif:

```bash
python3 scripts/create_env.py
# Atau via helper CLI: ./idx env
```

Contoh isi `.env` (lihat `.env.example`):

```text
IDX_AUTH_EMAIL=you@example.com
IDX_AUTH_PASSWORD=supersecret
# IDX_AUTH_TOKEN=Bearer ...
# IDX_PROXY=http://user:pass@proxy:3128
```

**PENTING:** Jangan commit `.env` ke repository. `.env` sudah ada di `.gitignore`.

### 6) Jalankan login interaktif sekali (selesaikan challenge Cloudflare)

Jalankan login interaktif untuk menyelesaikan challenge Cloudflare dan menyimpan Playwright storage state ke `~/.config/idx-scraper/playwright_storage_state.json`:

```bash
python3 export_idx_keywords_csv.py --output tmp_after_login.csv --login --login-email you@example.com --login-password "PASSWORD"
# Jika ingin menyimpan ke keyring: tambahkan --save-credentials
```

Atau lewat helper `idx`:

```bash
./idx login --email you@example.com --password "PASSWORD" --save-credentials
```

Setelah selesai, file storage state akan tersimpan di `~/.config/idx-scraper/playwright_storage_state.json` dan dapat digunakan untuk mode non-interaktif.

### 7) Jalankan mode otomatis/headless (non-interaktif)

Jika Anda sudah memiliki storage state yang valid (lihat langkah 6), jalankan:

```bash
python3 export_idx_keywords_csv.py --output out.csv --automated-playwright --headless
```

atau lewat helper `idx`:

```bash
./idx run --output out.csv --headless
```

Catatan: Jika Anda menjalankan di CI/cron dan storage state belum ada, gunakan `--persist-login` bersama kredensial (dengan aman melalui GitHub Secrets). Di lingkungan non-interaktif, script akan gagal cepat (exit code 2) jika kredensial tidak tersedia.

### 8) Contoh cron (jalankan setiap hari jam 02:00)

Contoh cron entry:

```cron
0 2 * * * cd /path/to/idx-scraper && /usr/bin/python3 export_idx_keywords_csv.py --output /path/to/output/idx_$(date +\%Y\%m\%d).csv --automated-playwright --headless
```

Pastikan storage state telah dibuat di mesin tersebut (lihat langkah 6) atau gunakan cara CI untuk menyimpan storage state/cred secara aman.

### 9) Contoh GitHub Actions (contoh penggunaan dengan Secrets)

File `.github/workflows/smoke.yml` disertakan sebagai contoh minimal untuk CI yang mem-verifikasi script dapat diimpor. Untuk workflow yang benar-benar menjalankan scraping secara non-interaktif, Anda harus menyiapkan Secrets `IDX_AUTH_EMAIL` dan `IDX_AUTH_PASSWORD`.

Contoh job GitHub Actions yang menggunakan Secrets (gunakan dengan hati-hati):

```yaml
name: scheduled-scrape
on:
  workflow_dispatch:
  schedule:
    - cron: '0 2 * * *'
jobs:
  run-scrape:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      - name: Install deps and browsers
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
          python -m playwright install
      - name: Run persisting login (headless)
        env:
          IDX_AUTH_EMAIL: ${{ secrets.IDX_AUTH_EMAIL }}
          IDX_AUTH_PASSWORD: ${{ secrets.IDX_AUTH_PASSWORD }}
        run: |
          python3 export_idx_keywords_csv.py --output out.csv --automated-playwright --headless --persist-login
```

**Keamanan:** GitHub Secrets harus disimpan di Settings → Secrets and variables → Actions; jangan commit kredensial ke repo. Perhatikan bahwa beberapa proteksi Cloudflare masih dapat meminta interaksi manusia di runner CI.

### 10) Menginstal helper `idx` ke PATH (opsional)

Gunakan skrip `install_idx.sh` untuk menyalin/symlink `idx` ke `/usr/local/bin` atau `~/.local/bin`:

```bash
./install_idx.sh
```

Setelah di-install Anda dapat memanggil `idx` dari mana saja:

```bash
idx run --output out.csv --headless
idx env    # untuk membuat .env secara interaktif
```

### 11) Troubleshooting singkat

- Playwright tidak ditemukan / browser belum ter-install:
  - Jalankan `python -m playwright install`.
- Headless run mengembalikan HTML (Cloudflare):
  - Jalankan `--interactive` atau `--login` di mesin lokal untuk menyelesaikan challenge dan menyimpan storage state.
- Skrip gagal di CI karena tidak ada kredensial:
  - Simpan `IDX_AUTH_EMAIL` dan `IDX_AUTH_PASSWORD` di GitHub Secrets dan gunakan `--persist-login`.
- Jangan commit storage state, cookie, atau `.env`.

### 12) Pengembangan & kontributor

- Untuk mengembangkan fitur baru, buat virtualenv, jalankan tests (jika ada), dan buat PR.
- Jika Anda ingin paket Python yang dapat diinstal, jalankan `pip install .` di root repo (pyproject.toml disediakan).

# IDX Scraper

Alat ini mengekspor pengumuman dari situs IDX (kolom: Kode_Emiten, Judul_Pengumuman, Tanggal_Pengumuman). README ini berisi panduan langkah-demi-langkah untuk menginstal, mengonfigurasi kredensial, melakukan login interaktif, menjalankan scraping secara headless, serta contoh penggunaan di cron dan GitHub Actions.

## Ringkasan singkat

- Pasang dependensi Python dan Playwright.
- Buat `.env` atau simpan kredensial di environment/keyring.
- Jalankan login interaktif sekali untuk menyelesaikan challenge Cloudflare.
- Setelah itu, jalankan mode headless (`--automated-playwright --headless`) untuk scraping non-interaktif.

---

## Panduan Langkah-demi-Langkah

Dokumentasi ini menjelaskan cara men-setup dan menjalankan alat IDX Scraper secara lokal, lewat cron, dan contoh penggunaan di CI (GitHub Actions). Semua contoh menggunakan shell Bash.

Catatan singkat: tool ini mengekspor kolom `Kode_Emiten`, `Judul_Pengumuman`, dan `Tanggal_Pengumuman` untuk kata kunci bawaan. Karena situs IDX memiliki proteksi (Cloudflare/JS), alat ini memakai Playwright untuk sesi yang memerlukan browser dan juga menyediakan jalur non-interaktif bila Anda sudah menyimpan Playwright storage state.

### 1) Clone repository

```bash
git clone <repo-url> idx-scraper
cd idx-scraper
```

### 2) Buat virtual environment (direkomendasikan)

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3) Pasang dependensi Python

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4) Install browser Playwright (wajib untuk mode Playwright)

Playwright membutuhkan browser binaries. Jalankan sekali di mesin Anda (akan mengunduh ~100+ MB):

```bash
python -m playwright install
```

### 5) Siapkan kredensial pengguna (aman)

Anda punya beberapa pilihan untuk menyimpan kredensial dan token:

- Gunakan file `.env` lokal (direkomendasikan untuk pengembangan lokal). Ada helper interaktif `scripts/create_env.py` untuk membuat `.env` dengan aman.
- Gunakan environment variables langsung: `IDX_AUTH_EMAIL`, `IDX_AUTH_PASSWORD`, `IDX_AUTH_TOKEN`, `IDX_PROXY`.
- Simpan di OS keyring (opsional): gunakan `--save-credentials` saat menjalankan `--login`.

Contoh membuat `.env` interaktif:

```bash
python3 scripts/create_env.py
# Atau via helper CLI: ./idx env
```

Contoh isi `.env` (lihat `.env.example`):

```text
IDX_AUTH_EMAIL=you@example.com
IDX_AUTH_PASSWORD=supersecret
# IDX_AUTH_TOKEN=Bearer ...
# IDX_PROXY=http://user:pass@proxy:3128
```

**PENTING:** Jangan commit `.env` ke repository. `.env` sudah ada di `.gitignore`.

### 6) Jalankan login interaktif sekali (selesaikan challenge Cloudflare)

Jalankan login interaktif untuk menyelesaikan challenge Cloudflare dan menyimpan Playwright storage state ke `~/.config/idx-scraper/playwright_storage_state.json`:

```bash
python3 export_idx_keywords_csv.py --output tmp_after_login.csv --login --login-email you@example.com --login-password "PASSWORD"
# Jika ingin menyimpan ke keyring: tambahkan --save-credentials
```

Atau lewat helper `idx`:

```bash
./idx login --email you@example.com --password "PASSWORD" --save-credentials
```

Setelah selesai, file storage state akan tersimpan di `~/.config/idx-scraper/playwright_storage_state.json` dan dapat digunakan untuk mode non-interaktif.

### 7) Jalankan mode otomatis/headless (non-interaktif)

Jika Anda sudah memiliki storage state yang valid (lihat langkah 6), jalankan:

```bash
python3 export_idx_keywords_csv.py --output out.csv --automated-playwright --headless
```

atau lewat helper `idx`:

```bash
./idx run --output out.csv --headless
```

Catatan: Jika Anda menjalankan di CI/cron dan storage state belum ada, gunakan `--persist-login` bersama kredensial (dengan aman melalui GitHub Secrets). Di lingkungan non-interaktif, script akan gagal cepat (exit code 2) jika kredensial tidak tersedia.

### 8) Contoh cron (jalankan setiap hari jam 02:00)

Contoh cron entry:

```cron
0 2 * * * cd /path/to/idx-scraper && /usr/bin/python3 export_idx_keywords_csv.py --output /path/to/output/idx_$(date +\%Y\%m\%d).csv --automated-playwright --headless
```

Pastikan storage state telah dibuat di mesin tersebut (lihat langkah 6) atau gunakan cara CI untuk menyimpan storage state/cred secara aman.

### 9) Contoh GitHub Actions (contoh penggunaan dengan Secrets)

File `.github/workflows/smoke.yml` disertakan sebagai contoh minimal untuk CI yang mem-verifikasi script dapat diimpor. Untuk workflow yang benar-benar menjalankan scraping secara non-interaktif, Anda harus menyiapkan Secrets `IDX_AUTH_EMAIL` dan `IDX_AUTH_PASSWORD`.

Contoh job GitHub Actions yang menggunakan Secrets (gunakan dengan hati-hati):

```yaml
name: scheduled-scrape
on:
  workflow_dispatch:
  schedule:
    - cron: '0 2 * * *'
jobs:
  run-scrape:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      - name: Install deps and browsers
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
          python -m playwright install
      - name: Run persisting login (headless)
        env:
          IDX_AUTH_EMAIL: ${{ secrets.IDX_AUTH_EMAIL }}
          IDX_AUTH_PASSWORD: ${{ secrets.IDX_AUTH_PASSWORD }}
        run: |
          python3 export_idx_keywords_csv.py --output out.csv --automated-playwright --headless --persist-login
```

**Keamanan:** GitHub Secrets harus disimpan di Settings → Secrets and variables → Actions; jangan commit kredensial ke repo. Perhatikan bahwa beberapa proteksi Cloudflare masih dapat meminta interaksi manusia di runner CI.

### 10) Menginstal helper `idx` ke PATH (opsional)

Gunakan skrip `install_idx.sh` untuk menyalin/symlink `idx` ke `/usr/local/bin` atau `~/.local/bin`:

```bash
./install_idx.sh
```

Setelah di-install Anda dapat memanggil `idx` dari mana saja:

```bash
idx run --output out.csv --headless
idx env    # untuk membuat .env secara interaktif
```

### 11) Troubleshooting singkat

- Playwright tidak ditemukan / browser belum ter-install:
  - Jalankan `python -m playwright install`.
- Headless run mengembalikan HTML (Cloudflare):
  - Jalankan `--interactive` atau `--login` di mesin lokal untuk menyelesaikan challenge dan menyimpan storage state.
- Skrip gagal di CI karena tidak ada kredensial:
  - Simpan `IDX_AUTH_EMAIL` dan `IDX_AUTH_PASSWORD` di GitHub Secrets dan gunakan `--persist-login`.
- Jangan commit storage state, cookie, atau `.env`.

### 12) Pengembangan & kontributor

- Untuk mengembangkan fitur baru, buat virtualenv, jalankan tests (jika ada), dan buat PR.
- Jika Anda ingin paket Python yang dapat diinstal, jalankan `pip install .` di root repo (pyproject.toml disediakan).

IDX Scraper
===========

Alat ini mengekspor pengumuman dari situs IDX (kolom: Kode_Emiten, Judul_Pengumuman, Tanggal_Pengumuman). README ini berisi panduan instalasi singkat dan langkah cepat untuk mulai menjalankan scraper secara lokal.

Petunjuk singkat:

- Pasang dependensi Python dan Playwright (lihat bagian berikutnya untuk langkah lengkap).
- Jalankan login interaktif sekali untuk menyelesaikan tantangan Cloudflare dan menyimpan Playwright storage state.
- Setelah storage state tersimpan, jalankan mode otomatis/headless untuk menghasilkan CSV secara terjadwal.
## IDX Scraper — Panduan Langkah-demi-Langkah

Dokumentasi ini menjelaskan cara men-setup dan menjalankan alat IDX Scraper secara lokal, lewat cron, dan contoh penggunaan di CI (GitHub Actions). Semua contoh menggunakan shell Bash.

Catatan singkat: tool ini mengekspor kolom Kode_Emiten, Judul_Pengumuman, dan Tanggal_Pengumuman untuk kata kunci bawaan. Karena situs IDX memiliki proteksi (Cloudflare/js), alat ini memakai Playwright untuk sesi yang memerlukan browser dan juga menyediakan jalur non-interaktif bila Anda sudah menyimpan Playwright storage state.

1) Clone repository
-------------------

```bash
git clone <repo-url> idx-scraper
cd idx-scraper
```

2) Buat virtual environment (direkomendasikan)
---------------------------------------------

```bash
python3 -m venv .venv
source .venv/bin/activate
```

3) Pasang dependensi Python
---------------------------
```markdown
# IDX Scraper

Alat ini mengekspor pengumuman dari situs IDX (kolom: Kode_Emiten, Judul_Pengumuman, Tanggal_Pengumuman). README ini berisi panduan langkah-demi-langkah untuk menginstal, mengonfigurasi kredensial, melakukan login interaktif, menjalankan scraping secara headless, serta contoh penggunaan di cron dan GitHub Actions.

---

## Ringkasan singkat

- Pasang dependensi Python dan Playwright.
- Buat `.env` atau simpan kredensial di environment / keyring.
- Jalankan login interaktif sekali untuk menyelesaikan challenge Cloudflare.
- Setelah itu, jalankan mode headless (`--automated-playwright --headless`) untuk scraping non-interaktif.
