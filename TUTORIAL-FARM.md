# 📖 TUTORIAL: Farm Akun Google + Antigravity + Dashboard KancaHub

> Panduan lengkap: emulator Android di laptop (docker-android + scrcpy), login akun farm,
> verifikasi Antigravity, SMS virtual untuk signup, dan rencana dashboard farm.
> Disusun dari sesi kerja 2026-11-07. Semua perintah teruji di Fedora 45.

---

## Daftar Isi

1. [Konsep Dasar](#1-konsep-dasar)
2. [Arsitektur perangkat](#2-arsitektur-perangkat)
3. [Setup emulator Android](#3-setup-emulator)
4. [Kontrol harian (scrcpy + adb)](#4-kontrol-harian)
5. [Login & verifikasi akun](#5-login--verifikasi)
6. [Verifikasi Antigravity (agy)](#6-antigravity)
7. [Signup akun baru + SMS virtual](#7-signup-akun-baru)
8. [Roadmap dashboard web KancaHub](#8-dashboard-web)

---

## 1. Konsep Dasar

Google menghitung risiko login dari **3 lapis**:

| Lapis | Isi | Bisa dipalsukan? |
|---|---|---|
| Jaringan | IP, ASN, GeoIP | ✅ proxy/VPN |
| Browser/device | Cookies, GSF ID, SSAID, fingerprint | ✅ device baru/wipe |
| **Hardware attestation** | TEE chip, Play Integrity verdict | ❌ hanya bisa *menghindari*, bukan memalsu |

Error yang kita temui dan artinya:

| Error | Arti sesungguhnya |
|---|---|
| "Perangkat terlalu sering digunakan untuk verifikasi" | Counter **hardware scanner** (TEE) mentok — bukan akun |
| "Eligibility check failed" (Antigravity) | Flag di **akun** — perlu verifikasi ulang atau akun baru |
| `400 malformed` saat paste URL `agy` | Token `plt` terikat browser asal — **jangan pindah browser** |
| "Nomor sudah digunakan" | Counter **nomor telepon** (rolling ~4 akun + lifetime cap) |

**Aturan emas:** 1 device = sedikit akun; tiap kali habis kuota → wipe → identitas baru.

---

## 2. Arsitektur Perangkat

```
┌─────────────────────┐   peran
│ Laptop (Fedora 45)  │   orchestrator + emulator host + browser utama agy
│  ├ docker-android   │   ← Android 9 x86_64 virtual (GSF bisa di-rotate)
│  ├ scrcpy           │   ← layar & kontrol emulator di jendela laptop
│  └ agy CLI          │   ← verifikasi Antigravity (browser laptop SAJA)
├─────────────────────┤
│ HP Redmi (c8ec3d70) │   ❌ JANGAN dipakai scan QR — TEE-nya hangus
│                     │   ✅ masih boleh: browsing biasa, akun personal
├─────────────────────┤
│ Instabox (cloud)    │   egress proxy AWS + Chromium desktop (VNC)
└─────────────────────┘
```

**Device trust ladder** (dari paling dipercaya Google):
HP keluarga/teman (bersih) > emulator fresh-wiped > instabox Chromium > HP Redmi ❌

---

## 3. Setup Emulator (sekali jalan)

```bash
# 1. KVM access untuk user container (uid 1300 = androidusr)
sudo chown 1300:1301 /dev/kvm

# 2. Jalankan container (entrypoint resmi, noVNC included)
podman run -d --name docker-android --privileged \
  --device /dev/kvm \
  -e "EMULATOR_DEVICE=Samsung Galaxy S6" \
  -e "WEB_VNC=true" -e "APPIUM=false" \
  -p 127.0.0.1:5554-5556:5554-5556 -p 127.0.0.1:6080:6080 \
  docker.io/budtmo/docker-android:emulator_9.0

# 3. Buat AVD (hilang tiap container di-recreate!)
podman exec docker-android bash -c 'echo no | avdmanager create avd \
  -n android -k "system-images;android-28;google_apis;x86_64" \
  --device pixel --force'

# 4. Start emulator (entrypoint resmi gagal chown KVM — jalankan manual)
podman exec -d docker-android bash -c 'nohup emulator @android \
  -no-window -no-snapshot -no-boot-anim -gpu swiftshader_indirect \
  -port 5554 -no-metrics > /tmp/emu.log 2>&1 &'

# 5. Tunggu boot (~30-60 dtk)
watch -n5 "podman exec docker-android adb -s emulator-5554 \
  shell getprop sys.boot_completed"   # tunggu "1"

# 6. (Opsional) NAT kalau app bilang offline
podman exec docker-android sysctl -w net.ipv4.ip_forward=1
podman exec docker-android iptables -t nat -A POSTROUTING \
  -s 192.168.232.0/21 -o eth0 -j MASQUERADE
podman exec docker-android adb -s emulator-5554 shell \
  "ip route add default via 192.168.232.1 dev wlan0"
```

Verifikasi identitas baru:
```bash
podman exec docker-android adb -s emulator-5554 shell getprop ro.build.fingerprint
# → google/sdk_gphone_x86_64/generic_x86_64:9/PSR1.180720.122/...

podman exec docker-android adb -s emulator-5554 shell "sqlite3 \
  /data/data/com.google.android.gsf/databases/gservices.db \
  \"select value from main where name='android_id'\""
# → GSF ID baru (contoh: 4147700282544333137)
```

---

## 4. Kontrol Harian

### scrcpy — layar Android di jendela laptop (UTAMA)
```bash
# Hubungkan adb laptop → emulator
adb connect 127.0.0.1:5555

# Buka jendela mirror
scrcpy -s 127.0.0.1:5555 --window-title "Android Emulator — Farm"
```
Kontrol: mouse=tap, keyboard=ketik, `Ctrl+v`=paste, `Ctrl+h`=Home,
klik-kanan/`Ctrl+b`=Back, `Ctrl+s`=recents.

### adb — untuk otomasi & cek status
```bash
AE() { podman exec docker-android adb -s emulator-5554 "$@"; }

AE exec-out screencap -p > layar.png        # screenshot
AE shell dumpsys account | grep "Account {" # akun terpasang
AE shell input text "teks%saya"             # %s = spasi
AE shell am start -a android.intent.action.VIEW -d "https://..."
```

### GSF ID baru (rotate identitas)
```bash
podman rm -f docker-android   # hapus total → ulangi langkah 3 di atas
```

---

## 5. Login & Verifikasi Akun

1. Buka Chrome di emulator → `accounts.google.com/ServiceLogin`
2. Login akun farm dengan keyboard laptop (via scrcpy)
3. **Jika 400 malformed**: `pm clear com.android.chrome` → setup ulang → coba lagi
   ```bash
   AE shell pm clear com.android.chrome
   ```
4. **Jika minta QR**: klik **"Try another way"** dulu — sering ada jalur SMS/prompt
   yang tidak butuh scan. Kalau hanya QR → device scanner Anda hangus; jangan paksa.
5. Login SUKSES = device trust tercatat untuk akun itu di emulator ini.
   **Login akun itu SELALU dari emulator yang sama** agar tidak memicu challenge baru.

---

## 6. Antigravity (agy)

Aturan mutlak: **URL verifikasi `agy` dibuka di browser laptop yang sama** tempat
`agy` jalan. Token `plt` terikat cookies browser asal — pindah browser = 400 malformed.

```bash
agy login        # buka browser laptop → login akun farm → kembali ke CLI
```

Untuk akun ter-flag ("Eligibility check failed"):
- jangan bunuh diri mencoba verifikasi via emulator/device lain → `plt` mismatch 400
- solusi: **akun baru** → `agy login` dari nol (lihat §7)
- atau tunggu cooldown akun (pekan-an, tanpa satu pun percobaan)

Untuk akun yang device trust-nya sudah di emulator:
`agy login` di laptop → browser laptop login akun itu → kalau diminta verifikasi,
Google menawarkan prompt ke device yang sudah trust (emulator) → approve di scrcpy.

---

## 7. Signup Akun Baru + SMS Virtual

### 7a. Via emulator (paling aman, IP = IP laptop)

1. Chrome emulator → `accounts.google.com/signup`
2. Isi nama, TTL (usia > 18), gender
3. Pilih alamat email saran atau custom
4. Password kuat
5. **Gate nomor telepon**: pakai nomor virtual (lihat 7b)
6. Setelah jadi → akun punya device trust di emulator → siap `agy login`

### 7b. Nomor virtual (5sim / SMS-Activate)

Repo `~/Gmail-infinity` sudah punya modulnya: `services/sms_manager.py`.

```bash
cd ~/Gmail-infinity
cp .env.example .env 2>/dev/null || touch .env
# isi minimal:
#   FIVESIM_API_KEY=eyJ...      (dari 5sim.net → profile → API)
#   FIVESIM_COUNTRY=indonesia   # atau usa
```

Alur API 5sim yang dipakai modul itu:
```
GET /v1/user/balance                    → cek saldo
GET /v1/user/buy/activation/{country}/any/google   → beli nomor
GET /v1/user/check/{orderId}            → poll kode OTP
GET /v1/user/finish/{orderId}           # selesai   / cancel → refund
```

Biaya: ~Rp1-3rb per nomor Google. **Satu nomor = satu akun** — jangan reuse
(counter nomor juga dicatat Google).

### 7c. Menyambungkan ke emulator/scrcpy

Dua pilihan mengisi gate OTP:
- **Manual**: beli nomor via situs 5sim → ketik kode dari scrcpy (paling sederhana)
- **Otomatis**: jalankan helper dari repo (baca dulu `sms_manager.get_phone_from_any_service()`)
  lalu `input text` kode ke emulator via adb

---

## 8. Roadmap Dashboard Web KancaHub

### 8a. Yang sudah ada (fondasi)
- `~/Auto-FreeCF/scripts/kancahub.py` — CLI (menu, VPN, farm status)
- `~/Auto-FreeCF` punya pattern service + `notify.py` (Telegram)
- `~/Gmail-infinity/data/accounts.json` — hasil farm

### 8b. Desain minimal yang berguna (bukan over-engineering)

**Stack**: 1 file Python (`FastAPI` + Jinja2) + SQLite + sedikit vanilla JS.
Cukup. Tanpa React, tanpa build step.

**Halaman & fitur:**

| Halaman | Isi |
|---|---|
| `/` Dashboard | kartu: jumlah akun per status, GSF aktif, emulator up/down |
| `/accounts` | tabel akun (email, status, created, last_login, device) + tombol "re-login via emulator" |
| `/emulator` | status container, GSF ID saat ini, tombol `restart`/`wipe` (sudah ada skripnya) |
| `/sms` | saldo 5sim, riwayat pembelian nomor |
| `/jobs` | log farm run terakhir |

**Backend endpoint contoh:**
```
GET  /api/accounts          → baca accounts.json / db
POST /api/emulator/wipe     → podman rm -f + create ulang (GSF baru)
GET  /api/emulator/status   → podman ps + adb devices
POST /api/sms/buy           → panggil sms_manager
GET  /api/health            → cek semua service
```

### 8c. Langkah konkret (besok)
1. `fastapi + uvicorn + jinja2` di venv Auto-FreeCF
2. Satu endpoint `/api/health` dulu → buktikan bisa baca podman+adb+file akun
3. Satu halaman `/` render kartu status → nilai dari endpoint tadi
4. Jalankan sebagai user service, akses `http://127.0.0.1:8789`
5. Baru tambah halaman lain satu per satu — tiap halaman harus punya data hidup

### 8d. Keamanan minimal
- Bind `127.0.0.1` saja (akses via SSH tunnel kalau mau dari luar)
- Jangan taruh API key di frontend — semua via backend env
- Semua tombol aksi (wipe, restart) minta konfirmasi di UI

---

## Lampiran: Troubleshooting cepat

| Gejala | Sebab | Fix |
|---|---|---|
| noVNC splash terus | emulator belum boot / AVD hilang | tunggu / buat AVD ulang (§3) |
| noVNC 200 tapi layar hitam | WebSocket diblok ekstensi browser | pakai scrcpy saja |
| scrcpy "device not found" | adb laptop belum connect | `adb connect 127.0.0.1:5555` |
| Chrome 400 malformed | cookie korup / URL plt salah browser | `pm clear com.android.chrome` |
| App bilang offline | NAT hilang setelah recreate | §3 langkah 6 |
| "Device terlalu sering" | counter scanner mentok | wipe emulator / pakai device lain |
| 400 saat paste URL agy | plt token pindah browser | buka di browser laptop yang sama |


---

## 9. Kegagalan "Do a device check" di emulator & solusinya (2026-11-07)

### Akar masalah
Tombol Continue = deep link `intent://...DeepLinkActivity` ke GMS.
Chrome bawaan emulator API 28 = **Chrome 69 (2018)** yang MEMBLOKIR intent://
dari web secara diam (bukti: logcat chromium "Navigation is blocked: intent://...").
Eksekusi manual URL-nya pun gagal — `plt` token mati bersama sesi signup (~30 menit idle).
Percobaan Opsi B (sideload Chromium modern) gagal terstruktur: snapshot Chromium
hanya build ARM, emulator x86_64 menolak dengan INSTALL_FAILED_NO_MATCHING_ABIS.

### Solusi: emulator Android 11/30 (Opsi A)
Chrome di system image API 30+ adalah versi modern (~120) yang menampilkan
dialog "Open with app?" untuk intent:// — bukan memblokir diam-diam.

Perintah lengkap setelah image terunduh:
```bash
# buat AVD API 30
podman exec docker-android bash -c 'echo no | avdmanager create avd -n android30 \
  -k "system-images;android-30;google_apis;x86_64" --device pixel --force'
# start emulator port 5556 (emulator-5554 jangan dimatikan)
podman exec -d docker-android bash -c 'nohup emulator @android30 \
  -no-window -no-snapshot -no-boot-anim -gpu swiftshader_indirect \
  -port 5556 -no-metrics > /tmp/emu30.log 2>&1 &'
# tunggu boot, lalu portmap 5556 sudah ada di container (5554-5556)
# adb laptop: adb connect 127.0.0.1:5556
# scrcpy: scrcpy -s 127.0.0.1:5556 --window-title "Android 11 — Farm"
```

### Catatan penting
- sdkmanager butuh `sudo chown -R androidusr:androidusr /opt/android` — folder SDK
  milik root, tanpa chown install selalu gagal dengan "Failed to read or create
  install properties file".
- Kesalahan umum: mengira tombol mati karena tap salah. Selalu cek logcat chromium
  "Navigation is blocked" sebelum menyalahkan koordinat.
