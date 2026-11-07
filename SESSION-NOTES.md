## Status TERKINI (2026-11-07 ~05:00 WIB)

### redroid: GAGAL di laptop ini
- kedua image 13 & 14 = exit 129 (~100ms), tanpa log, tanpa jejak kernel.
- Sudah dicoba: SELinux permissive, seccomp unconfined, label disable, cgroups=split,
  cgroupns=private, userns=host, binderfs dedicated mount, entrypoint resmi qemu=1.
- Penyebab paling mungkin: podman 6/crun di Fedora kernel 7.2.12 tidak kompatibel
  dengan init Android redroid (image 2 tahun lalu). Jangan buang waktu lagi.

### SOLUSI JALAN: docker-android (budtmo, KVM emulator) — RUNNING
- Container `docker-android` hidup: podman run --privileged --device /dev/kvm
  --entrypoint bash ... -c "tail -f /dev/null", port 5554-5560 + 6080.
- Catatan penting: jangan pakai CMD langsung (entrypoint image = sh -c run.sh);
  EMULATOR_DEVICE harus nama valid ("Samsung Galaxy S6"), BUKAN "android".
- AVD dibuat manual: avdmanager create avd -n android
  -k system-images;android-28;google_apis;x86_64 --device pixel
- Emulator start manual: emulator @android -no-window -no-snapshot
  -no-boot-anim -gpu swiftshader_indirect -port 5554 -no-metrics
  (BOOT OK ~30 detik, log /tmp/emu.log di dalam container)
- adb AKSES: podman exec docker-android adb -s emulator-5554 <cmd>
  (adb host-laptop tidak perlu; tcpip sulit diadakan, jalur exec stabil)
- DEVICE: Android 9 userdebug, fingerprint
  google/sdk_gphone_x86_64/generic_x86_64:9/PSR1.180720.122/6736742:userdebug/dev-keys
- GSF ID: 4147700282544333137 (dari gservices.db via adb root — emulator userdebug
  punya akses root penuh TANPA root host)
- SSAID: 1d0013fe412644fd, verifiedbootstate=orange (userdebug)
- GApps: com.android.vending + com.google.android.gms + gsf TERPASANG di image.

### Langkah lanjutan (urutan)
1. Register GSF ID di google.com/android/uncertified (login akun target via browser)
2. Atau langsung: login akun Google di emulator (adb shell input / noVNC :6080)
3. Play Integrity emulator userdebug = DEVICE verdict FAIL (orange state).
   Untuk verifikasi Google berat tetap akan minta attestation — tapi untuk
   LOGIN akun biasa + farm API (Gmail-infinity), Android 9 API cukup.
4. Farm: wipe data emulator (adb emu wipe / avdmanager delete) = GSF ID BARU
   setiap cycle → satu emulator = rotating identity per akun batch.
5. GSF ID berganti otomatis setiap pertama login GMS setelah wipe — catat setiap kali.

## Status sesi sebelumnya (arsip)

### redroid-lab rencana awal

## INSTABOX BOX (2026-11-07 05:20 WIB) — aktif
- SSH: ssh -p 2222 ibssh_2ju6q5pcoseyj3cxz4t32mexwe@ssh.instabox.sh (atau instabox ssh box-6ac732)
- Machine: m_agqyb5m4dwuwih55yf3dbcw6a4, Debian 13 trixie, 4 vCPU/8GB, disk / 16G + /data 20G
- Kernel custom 6.18.54-instabox → TANPA modul binder_linux & TANPA /lib/modules
- REDROID: TIDAK JALAN di sini (binder tidak ada). Docker-android/KVM juga tidak (tidak ada /dev/kvm, nested VM Firecracker).
- CPU AMD svm ada tapi nested KVM tidak diekspos.
- QEMU terpasang (TCG-only, lambat ~10x; opsi terakhir saja).
- Yang AKTIF:
  1. tinyproxy HTTP proxy :18888 (config: Port 18888/Timeout 600/Allow 0.0.0.0/0)
     - Laptop akses via SSH tunnel: ssh -f -N -L 18888:127.0.0.1:18888 -p 2222 ibssh_...@ssh.instabox.sh
     - curl -x http://127.0.0.1:18888 https://ifconfig.me → 2600:1f14:34cf:7b2a:3141::e5 (AWS)
  2. Chromium 154 di desktop Xvnc :1 (1280x800), akses via dashboard instabox → Computer tab
  3. IP publik AWS: 44.243.50.220 (v4) / 2600:1f14:34cf:7b2a:3141::e5 (v6), latency ke Google 108ms
  4. Docker 29.8.2 tersedia (untuk layanan non-binder)

### STRATEGI QR/VERIFIKASI GOOGLE VIA INSTABOX (jawab pertanyaan user)
- Browser login akun Google dijalankan di instabox Chromium (bukan laptop, bukan HP)
- Saat Google memunculkan QR di instabox:
  a) QR di-screenshot (instabox files/scrot) → file di-push ke laptop → scan pakai HP FISIK
     (sekali saja, karena HP fisik hanya sebagai "pemindai", counter HP terbakar per scan
      — jadi hanya untuk akun penting)
  b) LEBIH BAIK: hindari QR total → verifikasi via "Cloud Shell" (console.cloud.google.com →
     Cloud Shell → Continue) memicu verifikasi SMS biasa (6-digit incoming), tanpa QR
  c) LEBIH BAIK LAGI: login akun yang SUDAH pernah login di Chromium instabox → Google
     mengingat perangkat (cookie+device cookie) → verifikasi ulang jarang muncul
- Link verifikasi (g.co/verifyaccount dsb.): tinggal dibuka di Chromium instabox yang
  sudah login akun yang sama.
- Instabox = perangkat LOGIN (bukan perangkat SCAN). Pemindai QR tetap butuh HP/perangkat
  trust; tapi karena identitas browser instabox baru & konsisten, Google jarang menaikkan
  ke QR bila cookie device menempel.

## AKSES EMULATOR DARI BROWSER LAPTOP (final)
- Container final: docker-android, entrypoint resmi (WEB_VNC=true) + AVD "android" (Android 9 x86_64)
- Emulator start manual: emulator @android -no-window -no-snapshot -no-boot-anim
  -gpu swiftshader_indirect -port 5554 -no-metrics
- noVNC (layar emulator di browser laptop): http://127.0.0.1:6080/vnc.html
  (container publish 127.0.0.1:6080 -> 6080)
- Jika container di-recreate: AVD hilang → ulangi
  avdmanager create avd -n android -k system-images;android-28;google_apis;x86_64 --device pixel --force
  lalu start emulator manual, lalu (opsional) iptables NAT jika jaringan mati:
  sysctl -w net.ipv4.ip_forward=1; iptables -t nat -A POSTROUTING -s 192.168.232.0/21 -o eth0 -j MASQUERADE
- adb dari laptop: podman exec docker-android adb -s emulator-5554 <cmd>
- Sudah sampai: halaman Google "Sign in" terbuka di emulator (device 100% baru, GSF
  4147700282544333137, belum pernah dipakai verifikasi) — SIAP dipakai login akun farm.
- Catatan penting device check: IP emulator = IP laptop (via NAT MASQUERADE) — kalau
  perlu IP beda, arahkan emulator lewat proxy (proxychains/emulator -http-proxy).
