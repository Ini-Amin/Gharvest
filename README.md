TIDAK BEKERJA

# 📱 Emulator Farm — Android di Laptop (budtmo/docker-android + KVM)

> Satu sumber kebenaran untuk menjalankan, mengontrol, dan me-reset emulator Android
> untuk farm akun Google. Redroid/ayasa520 TIDAK jalan di laptop ini (binder tidak
> kompatibel podman/Fedora) — teknologi yang dipakai adalah **emulator QEMU+KVM**
> via image `budtmo/docker-android`, di-control **scrcpy**.

## Isi folder

| File | Untuk apa |
|---|---|
| `TUTORIAL-FARM.md` | Panduan lengkap: setup, login, Antigravity, SMS virtual, dashboard |
| `EMU-CHEATSHEET.txt` | Perintah harian: kontrol, status, reset |
| `auto_signup_cdp.py` | Otomasi signup via CDP (kontrol DOM, bukan koordinat) |
| `SESSION-NOTES.md` | Log sesi: apa yang dicoba, hasilnya, kenapa |

---

## QUICK START (yang sudah berjalan)

```bash
# 1. Container (sekali jalan; masih hidup selama tidak di-rm)
podman start docker-android           # kalau stop
podman exec docker-android avdmanager create avd -n android30ps \
  -k "system-images;android-30;google_apis_playstore;x86_64" --device pixel --force  # kalau AVD hilang

# 2. Emulator (di dalam container)
podman exec -d docker-android emulator @android30ps -no-window -no-snapshot \
  -gpu host -port 5554 -no-metrics

# 3. Kontrol dari laptop
adb connect 127.0.0.1:5555
scrcpy -s 127.0.0.1:5555 --window-title "Android 11 Farm"
```

Login akun → device check → selesai. Detail lengkap + troubleshooting: `TUTORIAL-FARM.md`.

---

## RESET IDENTITAS: apa yang di-reset, apa efeknya, dan kapan

Google mengenal perangkat lewat **beberapa lapis identitas**. Ketika Google minta QR
saat signup/login, ini artinya risk engine menandai kombinasi (IP + identitas device +
riwayat akun). Reset yang tepat tergantung lapis mana yang "hangus".

| # | Identitas | Apa itu | Cara reset | Efek | Kapan perlu |
|---|---|---|---|---|---|
| 1 | **SSAID** (`settings get secure android_id`) | Android ID per-app/per-user, 64-bit hex | Hapus data app: `pm clear <pkg>`, ATAU wipe AVD | App melihat "device baru" | App-level flag (jarang sendiri cukup) |
| 2 | **GSF ID / Android Device ID** | Identitas Google Services Framework — **yang utama** dihitung Google saat check-in | **Wipe AVD** (data.img baru) → GSF baru saat pertama check-in | Google melihat device **sama sekali baru** | **Setiap kali device limit terkena** / akun ter-flag dari device ini |
| 3 | **Fingerprint** (`ro.build.fingerprint`) | BUILD + versi Android + build number | Tergantung **system image** — ganti image = fingerprint baru (mis. android-28→android-30, google_apis→playstore) | Model device berubah total di mata Google | Kalau satu fingerprint sudah terlalu sering dipakai farm |
| 4 | **DroidGuard / Play Integrity verdict** | Hasil attestation runtime — `MEETS_DEVICE_INTEGRITY` dll | Bukan di-reset — **dihitung ulang** tiap request. Gagal karena: emulator detection, GMS usang, root, atau IP buruk | Verdict DEVICE harus jalan agar device check lolos | Kalau device check gagal/tidak bereaksi → cek `gms.unstable` proses hidup + versi GMS |
| 5 | **Check-in history (server-side)** | Riwayat akun yang pernah login/check-in dari GSF ID ini | **Tidak bisa di-reset dari sisi kita** — hanya dengan GSF ID baru | Riwayat lama hilang bersama GSF lama | Selalu menyertai reset #2 |
| 6 | **IP / risk network** | ASN, GeoIP, reputasi IP | Ganti egress (proxy/VPN/IP lain) | Risk score turun | Kalau QR muncul meski device fresh |

### Urutan reset yang benar (dari murah ke mahal)

```
1. pm clear app            → murah, 2 detik, app-level
2. Wipe AVD (data.img)     → GSF baru, ~1 menit, device-level  ← INI YANG PALING SERING DIPAKAI
3. Ganti system image      → fingerprint baru, ~15 menit (unduh image)
4. Ganti IP egress         → risk network baru, instan
5. Buat AVD baru + image baru + IP baru → identitas 100% fresh (full reset)
```

### Kenapa QR muncul saat signup/farm — dan cara merespons

QR saat **pembuatan akun** (bukan login) muncul karena salah satu/some:
- IP dianggap bot/datacenter → reset #4
- Fingerprint/GSF sudah terlalu sering buat akun → reset #2 (wipe AVD)
- Device check gagal jalan → cek #4 (DroidGuard) — jangan salah diagnosis
- Akun sebelumnya dari device ini di-flag → reset #2 + #4

**Yang TIDAK bisa di-reset:** counter di sisi akun (flag akun), riwayat nomor telepon
(jika sudah dipakai verifikasi), dan riwayat IP. Untuk itu → akun baru, nomor baru, IP baru.

---

## RESEP RESET CEPAT (paling sering dipakai)

### A. Reset GSF + SSAID saja (device "baru" di mata Google) — 2 menit

```bash
# 1. Matikan emulator
podman exec docker-android adb -s emulator-5554 emu kill 2>/dev/null; sleep 3

# 2. Hapus data AVD (GSF, SSAID, semua akun, semua app data = hilang)
podman exec docker-android bash -c 'rm -f ~/.android/avd/android30ps.avd/data.img \
  ~/.android/avd/android30ps.avd/cache.img ~/.android/avd/android30ps.avd/*.qcow2*'

# 3. Start ulang — GSF ID baru akan dibuat saat pertama check-in
podman exec -d docker-android emulator @android30ps -no-window -no-snapshot \
  -gpu host -port 5554 -no-metrics

# 4. Verifikasi GSF baru (setelah boot + ada internet)
adb connect 127.0.0.1:5555
podman exec docker-android adb -s emulator-5554 shell "sqlite3 \
  /data/data/com.google.android.gsf/databases/gservices.db \
  \"select value from main where name='android_id'\""
```

**CATATAN PENTING**: Akun-akun yang sudah login di emulator lama akan "hilang"
(device trust-nya hilang bersama GSF). Kalau akun itu masih perlu → login ulang
sekali untuk menanam device trust baru. Jadi **jangan wipe sembarangan** — wipe
hanya kalau device-nya yang di-flag, bukan akunnya.

### B. Full reset: AVD baru + image baru + fingerprint baru — 15 menit

```bash
# 1. Ganti image (pilih yang belum dipakai):
podman exec docker-android sdkmanager "system-images;android-31;google_apis_playstore;x86_64"

# 2. AVD baru dengan nama/device berbeda
podman exec docker-android avdmanager create avd -n farm2 \
  -k "system-images;android-31;google_apis_playstore;x86_64" --device pixel_4a --force

# 3. Start dengan profil berbeda
podman exec -d docker-android emulator @farm2 -no-window -no-snapshot \
  -gpu host -port 5558 -skin 1080x2340 -dpi 440 -no-metrics
```

### C. Reset IP (egress)

Emulator ikut IP laptop. Untuk IP berbeda per emulator:
```bash
podman exec -d docker-android emulator @android30ps \
  -http-proxy http://127.0.0.1:18888   # ← tinyproxy instabox via SSH tunnel
```
Atau ganti egress laptop (proxy_pool.py / warp / vpngate) — emulator otomatis ikut.

---

## QR VERIFICATION: emulator sebagai pemindai

QR "Verifikasi info Anda" saat signup/login di browser = **cross-device check**.
Pemindai harus: akun target SUDAH LOGIN di pemindai + lolos DroidGuard + counter OK.

**Catch-22 & solusinya:** untuk memindai QR login akun X, akun X harus dulu login
di emulator (sekali, password). Setelah itu emulator = device trust akun X dan bisa
memindai QR-nya di browser mana pun — HP fisik tidak perlu lagi.

```
1. Login akun X di emulator (scrcpy, isi email+password)
2. Kalau device check muncul → biarkan DroidGuard jalan (GMS modern sudah oke)
3. Setelah sukses → emulator = trusted device akun X
4. Berikutnya QR muncul di laptop → buka g.co/verify/xxx di Chrome emulator → confirm
```

HP Redmi (counter hangus) → **jangan pernah dipakai scan lagi**.

---

## PROFIL DEVICE (tidak terpaku Samsung S6)

`EMULATOR_DEVICE` hanya label. Profil asli: `avdmanager list device` — tersedia
Pixel 2–9 Pro Fold, Pixel Fold, Nexus 4–10, Tablet, Foldable, dst.

```bash
avdmanager create avd -n farm3 -k "system-images;android-30;google_apis_playstore;x86_64" \
  --device pixel_8 --force
emulator @farm3 -skin 1080x2400 -dpi 420
```

Fingerprint Google tetap `sdk_gphone_x86_64` (Google tahu itu emulator) — yang
menyelamatkan farm: **GSF baru per wipe + DroidGuard hidup + IP bersih**, bukan
penyamaran nama device. Profil berbeda hanya memvariasi SSAID-level telemetry.

---

## OTOMASI

### CDP (kontrol DOM web — yang terbukti bekerja)
```bash
adb forward tcp:9222 localabstract:chrome_devtools_remote
python3 ~/emulator-farm/auto_signup_cdp.py
```
Playwright modern menolak Chrome 83 (butuh ≥111) → script pakai websocket raw.

### scrcpy (kontrol manual + rekaman)
```bash
scrcpy -s 127.0.0.1:5555 --window-title "Farm"
# shortcut: Ctrl+h Home, Ctrl+b Back, Ctrl+v paste, klik-kanan=Back
```

### adb (status)
```bash
AE() { podman exec docker-android adb -s emulator-5554 "$@"; }
AE shell dumpsys account | grep "Account {"   # akun terpasang
AE exec-out screencap -p > layar.png          # screenshot
```

---

## STATUS TERKINI (2026-11-07)

- ✅ Android 11 Play Store (`android30ps`) — GMS 26.43.30, Play Store 53.9.23
- ✅ DroidGuard hidup (`com.google.android.gms.unstable` stabil, tidak crash)
- ✅ scrcpy jalan via `adb connect 127.0.0.1:5555`
- ✅ CDP otomasi siap (`auto_signup_cdp.py`)
- ⚠️ Sesi signup terakhir expired — mulai fresh saat farm lanjut
- ❌ Redroid/ayasa520 — dibuang, tidak kompatibel laptop ini
- ❌ HP Redmi sebagai pemindai — hangus, jangan dipakai
