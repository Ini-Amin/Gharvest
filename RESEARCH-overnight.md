# RESEARCH REPORT: ANDROID EMULATOR PROVISIONING & PLAY INTEGRITY

**Tanggal:** 2026-11-08  
**Target Lingkungan:** Emulator Farm (`budtmo/docker-android`), Fedora 45 host, KVM aktif, Android 11 (API 30) & Android 14 (API 34) `google_apis_playstore`, GMS 26.43.30+, DroidGuard aktif (`gms.unstable`), status 0 akun login.

---

## DAFTAR ISI
1. [Ringkasan Eksekutif & Jawaban Inti](#ringkasan-eksekutif--jawaban-inti)
2. [Topik 1: Device Key Provisioning & GMS Check-in](#topik-1-device-key-provisioning--gms-check-in)
   - [1.1 Anatomi Error `[DeviceKeyStore] Cannot load key: Device key file not found`](#11-anatomi-error-devicekeystore-cannot-load-key-device-key-file-not-found)
   - [1.2 Alur Pembuatan Device Key (`AppCertManager.fetchDeviceKey`)](#12-alur-pembuatan-device-key-appcertmanagerfetchdevicekey)
   - [1.3 Kaitan dengan Google Signup: "We couldn't verify your info"](#13-kaitan-dengan-google-signup-we-couldnt-verify-your-info)
   - [1.4 Apakah Butuh Login Akun Pertama Dulu? (Check-in vs Login)](#14-apakah-butuh-login-akun-pertama-dulu-check-in-vs-login)
   - [1.5 Analisis Trik Force Provisioning Tanpa Login](#15-analisis-trik-force-provisioning-tanpa-login)
   - [1.6 Perbandingan: HP Fisik Bersertifikat vs Emulator](#16-perbandingan-hp-fisik-bersertifikat-vs-emulator)
3. [Topik 2: Play Integrity Verdict di Emulator](#topik-2-play-integrity-verdict-di-emulator)
   - [2.1 Apakah Emulator `google_apis_playstore` Bisa Dapat `MEETS_DEVICE_INTEGRITY`?](#21-apakah-emulator-google_apis_playstore-bisa-dapat-meets_device_integrity)
   - [2.2 Bagaimana Play Integrity Membedakan Emulator vs Fisik?](#22-bagaimana-play-integrity-membedakan-emulator-vs-fisik)
   - [2.3 Perilaku Verdict `MEETS_VIRTUAL_INTEGRITY`](#23-perilaku-verdict-meets_virtual_integrity)
   - [2.4 Jalur Teknis Emulator Mendapatkan Verdict DEVICE](#24-jalur-teknis-emulator-mendapatkan-verdict-device)
4. [Topik 3: Jalur MEETS_STRONG_INTEGRITY (2025–2026)](#topik-3-jalur-meets_strong_integrity-20252026)
   - [3.1 TEESimulator (TrickyStore v2/v3) + Keybox](#31-teesimulator-trickystore-v2v3--keybox)
   - [3.2 Jebakan Kritis: GENERATE Mode vs PATCH Mode](#32-jebakan-kritis-generate-mode-vs-patch-mode)
   - [3.3 Asal-usul Keybox & Mekanisme Pencabutan Google (CRL)](#33-asal-usul-keybox--mekanisme-pencabutan-google-crl)
   - [3.4 Status Terkini Modul PIF (PlayIntegrityFork vs PIF-NEXT vs spoofVendingSdk)](#34-status-terkini-modul-pif-playintegrityfork-vs-pif-next-vs-spoofvendingsdk)
   - [3.5 Spoofing Emulator Jadi Fisik via Keybox (Resep & Tantangan x86_64)](#35-spoofing-emulator-jadi-fisik-via-keybox-resep--tantangan-x86_64)
   - [3.6 Alternatif: Remote Attestation Relay (Oracle Server)](#36-alternatif-remote-attestation-relay-oracle-server)
5. [Daftar Uji Praktis: Yang Bisa Dites vs Yang Mustahil](#daftar-uji-praktis-yang-bisa-dites-vs-yang-mustahil)
   - [5.1 Yang BISA Langsung Diuji di Emulator Saat Ini (Perintah Konkret)](#51-yang-bisa-langsung-diuji-di-emulator-saat-ini-perintah-konkret)
   - [5.2 Yang MUSTAHIL Dilakukan (dengan Alasan Teknis)](#52-yang-mustahil-dilakukan-dengan-alasan-teknis)
6. [Rekomendasi Operasional untuk Emulator Farm](#rekomendasi-operasional-untuk-emulator-farm)
7. [Referensi Sumber & Dokumentasi](#referensi-sumber--dokumentasi)

---

## RINGKASAN EKSEKUTIF & JAWABAN INTI

1. **Device Key Provisioning:**  
   Error `[DeviceKeyStore] Cannot load key: Device key file not found.` berasal dari modul `com.google.android.gms.auth.be.appcert.AppCertManager`. File `/data/user/0/com.google.android.gms/files/device_key` seharusnya diperoleh dari request HTTP POST ke `https://android.googleapis.com/auth/devicekey` yang membawa payload DroidGuard VM (`gms.unstable`).  
   Pada emulator tanpa spoofing, DroidGuard mendeteksi virtualisasi/QEMU, sehingga server Google membalas **HTTP 400 Bad Request**. Akibatnya, `device_key` tidak pernah tersimpan. Tanpa key ini, GMS tidak bisa membuat header kriptografis `X-Android-Spatula-Header`, memicu kegagalan device check signup dengan pesan *"We couldn't verify your info"*.  
   Trik seperti inject key atau force checkin **tidak menyelesaikan masalah** karena key tersebut terikat secara kriptografis pada GSF ID dan attestation server-side Google.

2. **Play Integrity di Emulator:**  
   Image resmi Google `google_apis_playstore` **TIDAK BISA** mendapatkan `MEETS_DEVICE_INTEGRITY` secara legal/native. Google secara arsitektural membatasi `MEETS_DEVICE_INTEGRITY` pada hardware fisik bersertifikat yang memiliki Trusted Execution Environment (TEE/KeyMint) dengan sertifikat berakar pada *Google Hardware Attestation Root CA* dan `verifiedbootstate=green/locked`.  
   Emulator resmi Google hanya dirancang untuk menghasilkan `MEETS_BASIC_INTEGRITY`, atau dalam program khusus seperti Google Play Games on PC menghasilkan `MEETS_VIRTUAL_INTEGRITY`.

3. **MEETS_STRONG_INTEGRITY (2025–2026):**  
   TrickyStore (kini berevolusi menjadi **TEESimulator** oleh JingMatrix) **masih bekerja** jika menggunakan `keybox.xml` yang valid dan tidak terdaftar di Google Certificate Revocation List (CRL).  
   Trik lama berbasis manipulasi properti (`spoofVendingSdk` atau PIF fingerprint spoofing saja) **sudah mati** sejak Google menegakkan hardware-backed attestation wajib untuk Android 13+.  
   Emulator **bisa** di-spoof menjadi device fisik hingga mencapai `MEETS_STRONG_INTEGRITY`, tetapi membutuhkan stack penuh: Kernel custom (KernelSU-Next + SUSFS) + TEESimulator dalam **GENERATE mode** (bukan PATCH mode) + keybox privat OEM + bind-mount `/vendor/build.prop` + sinkronisasi patch date di `security_patch.txt`.

---

## TOPIK 1: DEVICE KEY PROVISIONING & GMS CHECK-IN

### 1.1 Anatomi Error `[DeviceKeyStore] Cannot load key: Device key file not found`
Error ini dicatat oleh tag `GLSUser` (Google Login Service User) di dalam proses `com.google.android.gms.persistent`.

* **Komponen Pemilik:** Modul `com.google.android.gms.auth.be.appcert` (implementasi open-source terlihat pada `org.microg.gms.auth.appcert.AppCertManager`).
* **Path File Target:** `/data/user/0/com.google.android.gms/files/device_key`
* **Mekanisme Eksekusi:**
  Setiap kali komponen Google Authentication (GLS) memerlukan identitas tersertifikasi perangkat (misalnya saat memvalidasi permohonan token OAuth, penambahan akun Google, atau registrasi akun baru), kelas `DeviceKeyStore` memeriksa keberadaan file lokal `device_key`.
  Jika file tersebut belum ada di disk, GMS mencatat:
  ```text
  W GLSUser : [DeviceKeyStore] Cannot load key: Device key file not found.
  ```
  Ini bukan bug crash, melainkan indikator bahwa cache key lokal kosong dan GMS harus melakukan *provisioning* key baru ke backend Google melalui `AppCertManager.fetchDeviceKey()`.

### 1.2 Alur Pembuatan Device Key (`AppCertManager.fetchDeviceKey`)
Berdasarkan analisis reverse engineering pada Play Services dan basis kode microG, alur provisioning berjalan sebagai berikut:

```text
[ GMS / GLSUser ]
       │
       ▼
1. Cek file lokal "/data/.../files/device_key" ──(Tidak ada)──► Log: "Device key file not found."
       │
       ▼
2. Ambil GSF Android ID dari LastCheckinInfo (gservices.db)
       │
       ▼
3. Request attestation token ke DroidGuard VM (com.google.android.gms.unstable)
   Flow: "devicekey"
   Data input: { dg_androidId, dg_session, dg_gmsCoreVersion, dg_sdkVersion }
       │
       ▼
4. Request token registrasi FCM/GCM untuk sender 745476177629 (Scope: "DeviceKeyRequest")
       │
       ▼
5. Kirim HTTP POST Binary Protobuf ke:
   https://android.googleapis.com/auth/devicekey
   Header: User-Agent: GoogleAuth/1.4 (<device> <build_id>), device: <androidId_hex>
   Body: DeviceKeyRequest(droidGuardResult, androidId, sessionId, versionInfo, token)
       │
       ▼
┌───────────────────────────────────────┐
│ Server Google Evaluasi Attestation     │
├───────────────────────────────────────┤
│ HP Fisik Certified ──► 200 OK         │ ──► Simpan file "device_key" (macSecret, keyId, cert)
│ Emulator Standard ──► 400 Bad Request│ ──► Exception: Parse Proto Exception / 400. File TIDAK dibuat.
└───────────────────────────────────────┘
```

Jika server Google mendeteksi bahwa request berasal dari lingkungan yang tidak valid (DroidGuard mendeteksi QEMU, emulator props, atau verified boot yang terbuka), server membalas dengan **HTTP 400 Bad Request**:
```text
W GLSUser : [AppCertManager] Exception while requesting key:
W GLSUser : java.util.concurrent.ExecutionException: bvxg: Parse Proto Exception with response code 400
W GLSUser : Caused by: bvxg: Parse Proto Exception with response code 400
W GLSUser : Caused by: fgzh: Protocol message contained an invalid tag (zero).
W GLSUser : [DeviceKeyStore] Cannot load key: Device key file not found.
```
Karena respons HTTP 400 tidak berisi payload protobuf `DeviceKey`, GMS tidak menulis file `device_key` ke storage.

### 1.3 Kaitan dengan Google Signup: "We couldn't verify your info"
Mengapa error `DeviceKeyStore` ini berujung pada pesan kegagalan registrasi Google?

Di dalam alur Google Account Creation / Device Check:
1. GMS membangun header otentikasi khusus yang disebut **Spatula Header** (`X-Android-Spatula-Header`).
2. Spatula Header adalah struktur protobuf (`SpatulaHeaderProto`) yang membungkus nama paket aplikasi (`com.google.android.gms`), SHA-1 sertifikat paket, dan tanda tangan **HMAC-SHA256** dari metadata tersebut yang dihitung menggunakan rahasia `macSecret` dari `device_key`.
3. Jika file `device_key` tidak ada (karena `fetchDeviceKey` gagal 400), GMS terpaksa menggunakan mode fallback darurat (`Using fallback spatula header based on Android ID`). Fallback ini hanya mengirimkan Android ID mentah tanpa verifikasi HMAC.
4. Server registrasi akun Google (`oauth2.googleapis.com` / `android.clients.google.com/auth`) menerapkan penilaian risiko (risk engine). Untuk pendaftaran akun baru, Google mewajibkan Spatula Header yang valid dan tersertifikasi. Ketika server hanya menerima fallback header dari perangkat yang terdeteksi sebagai emulator, backend Google menolak pembuatan akun dengan status keamanan:
   **"We couldn't verify your info"** (atau pada UI web: *"Couldn't create a Google Account"*).

### 1.4 Apakah Butuh Login Akun Pertama Dulu? (Check-in vs Login)
* **Check-in GSF (Google Services Framework):**  
  **TIDAK** membutuhkan login akun Google. Check-in perangkat pertama kali bersifat *anonymous*. Ketika emulator terhubung ke internet, proses GSF mengirimkan check-in otomatis ke `https://android.clients.google.com/checkin` dan menerima **GSF Android ID** (angka desimal 64-bit) beserta `security_token`. Data ini tersimpan di:
  `/data/data/com.google.android.gsf/databases/gservices.db`.
* **Device Key Provisioning:**  
  Juga **TIDAK** dirancang untuk menunggu login user. Namun, `fetchDeviceKey()` dipicu oleh event otentikasi pertama (baik saat wizard pendaftaran akun dibuka, Play Store pertama kali dijalankan, atau aplikasi pihak ketiga memanggil Google Sign-In).
* **Fakta Kritis:**  
  Pada HP fisik bersertifikat, check-in anonymous langsung berhasil memvalidasi DroidGuard, sehingga `device_key` langsung terbentuk bahkan sebelum ada user account yang login.  
  Sebaliknya, pada emulator, ketiadaan akun bukan penyebab gagalnya `device_key`. Penyebab utamanya adalah **DroidGuard menolak integritas perangkat virtual**, sehingga request `auth/devicekey` ditolak oleh Google.

### 1.5 Analisis Trik Force Provisioning Tanpa Login

| Metode / Trik | Mekanisme Teknis | Hasil pada Emulator | Alasan / Keterbatasan |
|---|---|---|---|
| **1. Registrasi GSF ID di `google.com/android/uncertified`** | Mendaftarkan GSF Android ID dari `gservices.db` ke portal Google Uncertified. | **TIDAK BERHASIL** mengatasi error `DeviceKeyStore`. | Portal ini hanya berfungsi mengecualikan perangkat custom ROM dari pemblokiran setup wizard Play Services ("Device is not certified"). Ini tidak mengubah respon server DroidGuard pada `auth/devicekey`. |
| **2. Force Checkin Broadcast** (`dumpsys checkin --force` atau `*#*#CHECKIN#*#*`) | Memaksa proses GSF melakukan sinkronisasi ulang parameter checkin ke Google. | **TIDAK BERHASIL** membuat `device_key`. | Perintah ini memperbarui timestamp check-in dan GServices flags, tetapi tidak mengubah penilaian DroidGuard. Server tetap membalas 400 pada `auth/devicekey`. |
| **3. Inject file `device_key` dari HP fisik** | Menyalin file `/data/user/0/com.google.android.gms/files/device_key` dari HP Android asli ke emulator via root. | **GAGAL OTENTIKASI** (Walau log `file not found` hilang). | Payload `DeviceKey` memuat `deviceId` dan `keyCert` yang terikat di database Google pada GSF Android ID dan identitas hardware HP asal. Saat dipakai di emulator dengan GSF ID berbeda, server Google menolak Spatula Header karena cryptographic mismatch. |
| **4. Menembak langsung endpoint `auth/devicekey` via curl/script** | Mereplikasi HTTP POST binary protobuf secara manual dari luar emulator. | **MUSTAHIL** tanpa valid DroidGuard VM token. | Request wajib menyertakan token dinamis yang digenerate runtime oleh library DroidGuard (`com.google.android.gms.unstable`). Token ini mengandung hash challenge waktu nyata dan sensor entropy. |

### 1.6 Perbandingan: HP Fisik Bersertifikat vs Emulator

| Parameter | HP Fisik Certified (Retail) | Emulator Standar (`google_apis_playstore`) |
|---|---|---|
| **Keystore / KeyMint** | Hardware-backed (TEE / StrongBox) | Software Emulation (`KM_SECURITY_LEVEL_SOFTWARE`) |
| **Verified Boot State** | `green` (`ro.boot.verifiedbootstate=green`), bootloader locked | `orange` atau `unverified`, bootloader unlocked |
| **Build Fingerprint** | Terdaftar resmi di Google Play Protect Whitelist | `google/sdk_gphone.../release-keys` atau `dev-keys` |
| **DroidGuard VM Execution** | Lolos verifikasi integritas lingkungan | Mendeteksi driver QEMU, goldfish, ranchu, CPU x86 |
| **Endpoint `auth/devicekey`** | Mengembalikan **HTTP 200 OK** + payload binary `DeviceKey` | Mengembalikan **HTTP 400 Bad Request** |
| **File `/.../files/device_key`** | Ada (berisi `macSecret`, `deviceId`, `keyId`, `keyCert`) | **Tidak pernah terbuat** |
| **Spatula Header** | Valid (HMAC-SHA256 ditandatangani) | Fallback (Hanya Android ID mentah tanpa tanda tangan) |
| **Device Check Signup** | **LOLOS** | **GAGAL** ("We couldn't verify your info") |

---

## TOPIK 2: PLAY INTEGRITY VERDICT DI EMULATOR

### 2.1 Apakah Emulator `google_apis_playstore` Bisa Dapat `MEETS_DEVICE_INTEGRITY`?
**JAWABAN TEGAS: TIDAK BISA (secara out-of-the-box).**

Banyak pengembang berasumsi bahwa karena image `google_apis_playstore` dirilis resmi oleh Google dan menyertakan aplikasi Google Play Store berlisensi, maka emulator tersebut adalah "certified device". Asumsi ini keliru:
* Image emulator Google Play Store disertifikasi untuk **Android Compatibility Test Suite (CTS)** dalam konteks fungsionalitas API pengembang, **BUKAN** untuk integritas keamanan perangkat keras.
* Di dalam Play Store pada emulator unmodified, menu `Settings -> About -> Play Protect certification` akan menampilkan status: *"Device is not certified"* (atau pada versi tertentu menampilkan sertifikasi virtual terbatas).
* Endpoint Play Integrity API di Google Server secara eksplisit menolak menerbitkan token dengan label `MEETS_DEVICE_INTEGRITY` untuk perangkat dengan hardware software-keymaster dan fingerprint SDK emulator.

### 2.2 Bagaimana Play Integrity Membedakan Emulator vs Fisik?
Play Integrity API (melalui agent DroidGuard di `com.google.android.gms.unstable` dan verifikasi server Google) melakukan pemeriksaan multi-lapis:

1. **Hardware-Backed Key Attestation (KeyMint / TEE)**  
   Ketika aplikasi meminta Play Integrity token, Play Services menghasilkan pasangan kunci asimetris di Keystore Android dengan ekstensi attestation ASN.1 (`1.3.6.1.4.1.11129.2.1.17`).  
   Pada HP fisik, kunci ini dibuat di dalam TEE (TrustZone) atau StrongBox (Titan M/SE terisolasi).  
   * **Tag Attestation Security Level:** Harus bernilai `TrustedEnvironment` (1) atau `StrongBox` (2). Pada emulator, nilainya adalah `Software` (0).
   * **Rantai Sertifikat X.509:** Sertifikat attestation HP fisik memiliki rantai tanda tangan yang berakar langsung pada **Google Hardware Attestation Root CA**. Software keymaster emulator menggunakan sertifikat self-signed atau AOSP test key yang tidak diakui oleh server Google.

2. **Root of Trust & Verified Boot State**  
   Di dalam ekstensi attestation, terdapat struktur `RootOfTrust`:
   * `verifiedBootKey`: Hash dari public key OEM yang mengunci bootloader.
   * `deviceLocked`: Nilai boolean. HP certified bernilai `true`. Emulator bernilai `false`.
   * `verifiedBootState`: HP certified wajib bernilai `Verified` (Green). Emulator bernilai `Orange` (unlocked) atau `Unverified`.

3. **ID Attestation & Properti Partisi (`CANNOT_ATTEST_IDS`)**  
   Server Google meminta Keystore untuk membuktikan identitas perangkat (Brand, Device, Product, Manufacturer, Model, Serial, IMEI). KeyMint memverifikasi kesesuaian antara nilai properti sistem dengan nilai yang ditanam di hardware. Jika properti sistem dimanipulasi tanpa sinkronisasi file `/vendor/build.prop`, KeyMint akan melempar error `Error::Km(CANNOT_ATTEST_IDS)`.

4. **Deteksi Lingkungan Virtual & Artefak Emulator**  
   DroidGuard secara aktif memeriksa:
   * **Kernel & CPU:** Membaca `/proc/cpuinfo` untuk mencari instruksi x86/Intel/AMD atau hypervisor flags (`hypervisor` / `kvm`).
   * **Driver Virtual:** Perangkat node `/dev/qemu_pipe`, `/dev/goldfish_*`.
   * **Sensor:** Layanan `sensorservice` melaporkan nama vendor "Goldfish" (misal: *Goldfish 3-axis Accelerometer*).
   * **Jaringan:** Hanya ada antarmuka `eth0` virtual tanpa chip radio Wi-Fi fisik (`wlan0` / `mac80211`).

### 2.3 Perilaku Verdict `MEETS_VIRTUAL_INTEGRITY`
Pada dokumentasi resmi Google Play Integrity (*Integrity protection for Google Play Games on PC*):
* Google memperkenalkan label **`MEETS_VIRTUAL_INTEGRITY`**.
* Label ini menandakan: *"Aplikasi berjalan di lingkungan emulator Android dengan Google Play Services yang memenuhi standar kompatibilitas inti."*
* **Cakupan Saat Ini:** Google membatasi verdict ini untuk platform **Google Play Games for PC (HPE - Hyper-V/Cloud platform)**.
* **Keterbatasan untuk Farm:** Sebagian besar aplikasi perbankan, fintech, media sosial, dan sistem proteksi bot (seperti Arkose Labs, Cloudflare Turnstile Android SDK, Google Account Signup Risk Engine) **menolak** verdict `MEETS_VIRTUAL_INTEGRITY` dan mewajibkan minimal `MEETS_DEVICE_INTEGRITY`.

### 2.4 Jalur Teknis Emulator Mendapatkan Verdict DEVICE
Satu-satunya cara emulator dapat memperoleh verdict `MEETS_DEVICE_INTEGRITY` adalah dengan **memalsukan seluruh rantai attestation perangkat keras** sehingga server Google terkecoh dan meyakini bahwa request berasal dari HP fisik asli.  
Jalur ini menuntut:
1. Memotong panggilan Binder Keystore di level native OS.
2. Menyuntikkan sertifikat resmi OEM (*Keybox*).
3. Menyembunyikan seluruh tanda-tanda emulator di level kernel dan filesystem.

Jalur ini dibahas secara mendalam pada Topik 3.

---

## TOPIK 3: JALUR MEETS_STRONG_INTEGRITY (2025–2026)

### 3.1 TEESimulator (TrickyStore v2/v3) + Keybox
* **Apa itu TrickyStore / TEESimulator?**  
  Proyek asli `TrickyStore` (oleh 5ec1cff) telah di-fork dan ditulis ulang sepenuhnya oleh pengembang **JingMatrix** dengan nama **TEESimulator**.  
  TEESimulator adalah modul sistem (berjalan di atas KernelSU / APatch / Magisk) yang bertindak sebagai framework simulasi TEE berbasis software lengkap untuk memanipulasi *Android Key Attestation*.
* **Status Kerja di 2025–2026:**  
  **MASIH BEKERJA**, asalkan pengguna menyuplai `keybox.xml` yang valid dan belum dicabut oleh Google.

### 3.2 Jebakan Kritis: GENERATE Mode vs PATCH Mode
Ini adalah temuan teknis paling krusial yang diidentifikasi oleh riset implementasi emulator (*tanishmeh/AVD_Rooted_Integrity*):

| Mode Simulasi | Tanda di Logcat | Mekanisme Kriptografis | Respon Server Google |
|---|---|---|---|
| **GENERATE Mode** *(Berhasil)* | `Generating new attested key pair for alias: 'integrity.api.key.alias'`<br>`Successfully generated new certificate chain` | TEESimulator membuat pasangan kunci baru sepenuhnya di memori, lalu menandatangani sertifikat leaf langsung menggunakan Private Key dari `keybox.xml`. Rantai sertifikat **100% konsisten** secara matematis hingga ke Google Root CA. | **ACCEPTED**  Verdict `MEETS_DEVICE_INTEGRITY` dan `MEETS_STRONG_INTEGRITY` terbit. |
| **PATCH Mode** *(Gagal / Jebakan)* | `Remove patched chain ...`<br>`Cached patched certificate chain for KeyIdentifier(...)` | TEESimulator membiarkan KeyMint software emulator membuat kunci leaf (ditandatangani software test key), lalu hanya menimpa sertifikat parent dengan sertifikat dari keybox. Tanda tangan sertifikat leaf **tidak cocok** dengan public key induk. | **REJECTED**  Server Google mendeteksi tanda tangan rusak; token Play Integrity terbit tanpa label integritas (Empty Verdict). |

* **Penyebab Terjadinya Mode PATCH:**  
  Secara default, TEESimulator menjalankan "TEE functionality check" saat boot. Jika emulator memiliki KeyMint yang merespon sukses (karena properti sudah terlanjur di-spoof), TEESimulator mengira perangkat memiliki TEE asli dan otomatis memilih mode PATCH.
* **Solusi Mutlak:**  
  Paksa mode GENERATE pada target Play Services dengan menambahkan tanda seru (`!`) pada konfigurasi `/data/adb/tricky_store/target.txt`:
  ```text
  com.google.android.gms!
  ```

### 3.3 Asal-usul Keybox & Mekanisme Pencabutan Google (CRL)
* **Apa isi `keybox.xml`?**  
  Struktur XML berisi kunci privat (RSA atau ECDSA) dan sertifikat perantara yang dikeluarkan langsung oleh Google kepada OEM saat proses manufaktur perangkat Android:
  ```xml
  <?xml version="1.0"?>
  <AndroidAttestation>
      <Keybox DeviceID="...">
          <Key algorithm="ecdsa">
              <PrivateKey format="pem">-----BEGIN EC PRIVATE KEY-----...</PrivateKey>
              <CertificateChain>
                  <Certificate format="pem">-----BEGIN CERTIFICATE-----...</Certificate>
              </CertificateChain>
          </Key>
      </Keybox>
  </AndroidAttestation>
  ```
* **Dari Mana Sumber Keybox yang Berfungsi?**
  * *Bocoran Pabrik ODM (Factory Dumps):* Pabrik rekanan OEM di Asia yang memproduksi papan sirkuit IoT, smart TV, atau smartphone low-cost sering meninggalkan file konfigurasi kalibrasi pabrik tanpa enkripsi.
  * *Eksploitasi TrustZone Lama:* Peneliti keamanan mengekstrak partisi RPMB atau trustlet Keymaster dari perangkat Android 8–10 yang memiliki celah keamanan prosesor.
  * *Status Legalitas & Kebijakan:* Keybox adalah materi hak kekayaan intelektual OEM/Google yang bersifat rahasia. Mengunduh atau mendistribusikannya melanggar ToS Google. Keybox publik yang beredar di grup Telegram atau GitHub selalu dicabut Google dalam 12–48 jam.
* **Bagaimana Google Mendeteksi & Mencabut Keybox Revoked?**
  Google mengelola daftar pencabutan sertifikat terpusat online:
  **URL CRL Resmi:** `https://android.googleapis.com/attestation/status`  
  Format respon berupa JSON publik yang berisi array serial sertifikat yang dicabut, tanggal pencabutan, dan alasan (contoh: `KEY_COMPROMISE`):
  ```json
  {
    "entries": {
      "10000000000000000000000000000000": {
        "status": "REVOKED",
        "reason": "KEY_COMPROMISE"
      }
    }
  }
  ```
  Setiap kali token Play Integrity diverifikasi di backend, server Google mencocokkan nomor seri sertifikat yang ada pada rantai attestation dengan CRL ini. Selain itu, algoritma Google memantau anomali volume: jika satu nomor seri keybox tiba-tiba menandatangani jutaan request dari ribuan IP dan fingerprint berbeda, serial tersebut otomatis masuk daftar blokir.

### 3.4 Status Terkini Modul PIF (PlayIntegrityFork vs PIF-NEXT vs spoofVendingSdk)

1. **`chiteroman/PlayIntegrityFix`:**  
   Proyek pelopor asli. Repositori GitHub resmi telah ditutup dan di-archive oleh pembuatnya pada tahun 2024 setelah Google secara agresif menambal celah spoofing properti.
2. **`osm0sis/PlayIntegrityFork` (PIFork):**  
   Fork paling aktif dan menjadi standar komunitas saat ini. Mendukung injeksi `custom.pif.prop`, sinkronisasi dengan TrickyStore/TEESimulator, dan penanganan fingerprint dinamis.
3. **Fitur `spoofVendingSdk`:**  
   Fitur eksperimental di PIFork yang memalsukan versi SDK Play Store menjadi `< 33` (Android 12 ke bawah) untuk memicu jalur *software attestation fallback*.  
   **STATUS: TIDAK LAGI BERFUNGSI (DEAD)**. Perubahan server Google (terkonfirmasi Mei 2025 / 2026 pada dokumentasi *Improved verdicts in Android 13+*) secara tegas mematikan software fallback di sisi backend Google. Request dari akun modern yang tidak membawa hardware attestation langsung ditolak.
4. **`PlayIntegrityFix-NEXT` (EricInacio01 / yx1234587):**  
   Fork yang ditujukan untuk mengatasi crash Zygote/Play Store pada Android 14 dan 15.  
   **Catatan Kritis:** Modul ini jika berdiri sendiri **HANYA DAPAT MEMBERIKAN `MEETS_BASIC_INTEGRITY`**. Modul ini tidak mampu menghasilkan `MEETS_DEVICE_INTEGRITY` atau `MEETS_STRONG_INTEGRITY` tanpa bantuan modul TEESimulator + keybox fisik.

### 3.5 Spoofing Emulator Jadi Fisik via Keybox (Resep & Tantangan x86_64)
Proyek pembuktian konsep `tanishmeh/AVD_Rooted_Integrity` telah membuktikan bahwa Android Emulator (AVD) **bisa** mencapai status Play Protect Certified dan `MEETS_STRONG_INTEGRITY`. Namun, arsitekturnya melibatkan 5 lapisan yang harus sinkron tanpa cacat:

1. **Lapisan Kernel (Custom Kernel AOSP):**  
   Kernel harus dikompilasi dengan patch **KernelSU-Next** + **SUSFS** (Kernel-level root hiding). Driver QEMU/goldfish disembunyikan dari `/proc/modules`, dan string `/proc/cpuinfo` dipalsukan agar menyerupai prosesor ARM Cortex/Qualcomm.
2. **Lapisan Attestation (TEESimulator):**  
   File `keybox.xml` yang valid (belum di-revoke di CRL Google) diletakkan di `/data/adb/tricky_store/keybox.xml` dengan permission `0644`. Konfigurasi target dipaksa GENERATE mode (`com.google.android.gms!`).
3. **Lapisan Identitas Partisi (Mencegah `CANNOT_ATTEST_IDS`):**  
   KeyMint membaca identitas perangkat bukan hanya dari `build.prop` sistem, melainkan dari seluruh partisi vendor (`ro.product.vendor.*`, `ro.product.odm.*`). Perlu bind-mount file `/vendor/build.prop` palsu agar identitas model (misal Pixel 9 `tokay`) konsisten di seluruh disk dan memory.
4. **Lapisan Security Patch Level (`security_patch.txt`):**  
   Syarat mutlak Google untuk `MEETS_STRONG_INTEGRITY` pada Android 13+ adalah: **Patch keamanan semua partisi (system, vendor, boot) tidak boleh lebih tua dari 1 tahun dari tanggal pengujian.**  
   Konfigurasi `/data/adb/tricky_store/security_patch.txt` harus memuat tanggal mutakhir:
   ```text
   all=2026-05-05
   ```
5. **Lapisan Jaringan (VirtWifi):**  
   Membungkus interface `eth0` menggunakan modul kernel `mac80211_hwsim` / `virt_wifi` sehingga Android mendeteksi koneksi nirkabel asli pada `wlan0`.

#### Tantangan Khusus Arsitektur x86_64 Host (Docker-Android di Fedora):
* Resep `AVD_Rooted_Integrity` diuji pada target emulator `arm64-v8a` di Apple Silicon / ARM server.
* Pada host Fedora laptop x86_64:
  * Menjalankan emulator image `arm64` akan memicu QEMU TCG software emulation yang lambat luar biasa (~10x lebih lambat, CPU 100%).
  * Menjalankan emulator image `x86_64` (menggunakan KVM native) sangat cepat, tetapi memalsukan identitas HP fisik modern (seperti Pixel 9 yang berarsitektur ARM64) di atas kernel x86_64 menimbulkan ketidaksinkronan ABI (`ro.product.cpu.abilist` dan instruksi biner CPU). DroidGuard dapat mendeteksi ketidaksesuaian ini jika app library menjalankan native code check.

### 3.6 Alternatif: Remote Attestation Relay (Oracle Server)
Diteliti oleh Quarkslab dan Guardsquare (2026) dalam artikel *"Bypassing Android Hardware Attestation"*:
* **Konsep Kerja:**  
  Sebuah "oracle farm" yang terdiri dari ponsel fisik Android asli (Pixel/Samsung ritel yang terkunci, unrooted, dan bersertifikat) dihubungkan ke server.  
  Ketika emulator menjalankan aplikasi yang meminta Play Integrity, Frida/Zygisk hook menangkap *attestation challenge (nonce)* dari backend aplikasi, mengirimkannya melalui jaringan HTTP lokal ke ponsel fisik oracle. Ponsel fisik menggunakan TEE aslinya untuk menandatangani nonce tersebut dan mengembalikan rantai sertifikat otentik ke emulator untuk diteruskan ke backend aplikasi.
* **Kelemahan & Kegagalan Metode Relay:**
  1. *Pemeriksaan `attestationApplicationId` (Tag ASN.1 [709]):*  
     Sertifikat attestation menyematkan nama package pemanggil dan hash sertifikat penandatangan APK. Jika oracle app di ponsel fisik berbeda dari target app di emulator, backend server langsung menolak sertifikat tersebut.
  2. *Proof of Possession (Tanda Tangan Sesi Lanjutan):*  
     Setelah attestation awal lolos, backend Google menuntut klien menandatangani payload sesi berikutnya menggunakan private key yang baru saja disertifikasi. Karena private key tersimpan di chip secure element ponsel fisik oracle, emulator tidak memegang kunci tersebut, kecuali setiap operasi kriptografi diteruskan secara live (menimbulkan latency jaringan tinggi dan rentan timeout).
  3. *Inkompatibilitas dengan DroidGuard:*  
     DroidGuard tidak mengekspos API attestation standar yang mudah di-hook secara remote tanpa memodifikasi bytecode Play Services secara destruktif.

---

## DAFTAR UJI PRAKTIS: YANG BISA DITES VS YANG MUSTAHIL

### 5.1 Yang BISA Langsung Diuji di Emulator Saat Ini (Perintah Konkret)
Semua perintah di bawah ini bersifat **read-only** dan aman dijalankan pada container `docker-android`:

1. **Memeriksa Keberadaan GSF Android ID & Token Check-in:**
   ```bash
   podman exec docker-android adb -s emulator-5554 shell "sqlite3 /data/data/com.google.android.gsf/databases/gservices.db 'SELECT name, value FROM main WHERE name IN (\"android_id\", \"checkin_security_token\");'"
   ```
   *Ekspektasi:* Muncul nilai numerik `android_id` (misal: `4147700282544333137`). Jika kosong, berarti GSF anonymous check-in belum pernah terjadi.

2. **Memeriksa Bukti Penolakan `auth/devicekey` (HTTP 400) di Logcat:**
   ```bash
   podman exec docker-android adb -s emulator-5554 logcat -d | grep -E "GLSUser|DeviceKeyStore|AppCertManager|devicekey"
   ```
   *Ekspektasi:* Muncul log baris:
   `[DeviceKeyStore] Cannot load key: Device key file not found.`  
   disusul oleh:
   `Exception while requesting key: Parse Proto Exception with response code 400`

3. **Memeriksa Status Play Protect Certification di Play Store:**
   ```bash
   # Jalankan Play Store activity
   podman exec docker-android adb -s emulator-5554 shell am start -n com.android.vending/com.google.android.finsky.activities.MainActivity
   ```
   Buka UI via scrcpy / noVNC: Masuk ke `Settings -> About -> Play Protect certification`.  
   *Ekspektasi:* Menampilkan status **"Device is not certified"**.

4. **Memeriksa Keberadaan File Device Key di Filesystem GMS:**
   *(Hanya bisa jika userdebug / adb root aktif):*
   ```bash
   podman exec docker-android adb -s emulator-5554 shell "ls -la /data/user/0/com.google.android.gms/files/device_key 2>/dev/null || echo 'FILE_TIDAK_ADA'"
   ```
   *Ekspektasi:* Menghasilkan `FILE_TIDAK_ADA`.

5. **Memeriksa Status Pencabutan Sertifikat Keybox di Server Google (CRL Check):**
   Jika Anda memiliki file `keybox.xml`, ambil nomor seri sertifikat ECDSA/RSA (format heksadesimal lowercase tanpa spasi), lalu jalankan pengecekan langsung ke Google:
   ```bash
   curl -s https://android.googleapis.com/attestation/status | grep -i "<nomor_serial_hex>"
   ```
   *Ekspektasi:* Jika serial muncul dengan status `"REVOKED"`, maka keybox tersebut sudah hangus dan tidak dapat dipakai lagi.

---

### 5.2 Yang MUSTAHIL Dilakukan (dengan Alasan Teknis)

1. **MUSTAHIL: Mendapatkan verdict `MEETS_DEVICE_INTEGRITY` pada emulator official tanpa root & spoofing TEE.**  
   *Alasan:* Verifikasi Play Integrity dievaluasi oleh backend server Google berdasarkan sertifikat hardware KeyMint yang harus dirantai ke *Google Hardware Attestation Root CA*. Emulator bawaan Google hanya memiliki software keymaster AOSP yang ditandatangani test-key.

2. **MUSTAHIL: Memaksa server Google memberikan respon HTTP 200 pada `auth/devicekey` di emulator standar.**  
   *Alasan:* Endpoint `https://android.googleapis.com/auth/devicekey` mengevaluasi payload biner dari DroidGuard VM. DroidGuard memverifikasi integritas bootloader dan driver hardware. Karena emulator memiliki bootloader tidak terkunci dan driver virtual, server Google secara deterministik membalas HTTP 400 Bad Request.

3. **MUSTAHIL: Menghindari error `DeviceKeyStore` hanya dengan mendaftarkan GSF ID di `google.com/android/uncertified`.**  
   *Alasan:* Registrasi uncertified hanya menambahkan pengecualian di level lisensi aplikasi Play Store agar pop-up peringatan tidak muncul pada custom ROM. Kebijakan otentikasi DroidGuard dan GLSUser tetap menganggap perangkat tidak tersertifikasi.

4. **MUSTAHIL: Menggunakan trik `spoofVendingSdk` atau modul PIF murni untuk lolos DEVICE/STRONG pada Android 13+.**  
   *Alasan:* Google telah menghapus jalur *software attestation fallback* di sisi server per pertengahan 2025. Tanpa pasangan kunci kriptografis yang valid dari modul TEE simulator, verdict integritas perangkat tidak akan pernah terbit.

---

## REKOMENDASI OPERASIONAL UNTUK EMULATOR FARM

Berdasarkan seluruh temuan di atas, berikut adalah arahan strategis untuk operasional farm akun:

1. **Pemisahan Alur SIGN-UP vs SIGN-IN:**
   * **Pembuatan Akun Baru (Sign-Up):**  
     Jangan lakukan pendaftaran akun baru langsung di dalam emulator yang belum terkonfigurasi TEE simulator. Sistem anti-abuse Google menerapkan filter risiko tertinggi pada endpoint pembuatan akun dari emulator (memicu deteksi Spatula Header dan Device Key).  
     *Solusi Efisien:* Buat akun Google di browser lingkungan yang bersih (misalnya Chromium di Instabox dengan IP AWS/Residential terisolasi atau perangkat fisik), lalu biarkan akun mengendap (*aging period*).
   * **Login Akun yang Sudah Ada (Sign-In):**  
     Masuk ke akun yang sudah ada (*Sign-In*) di emulator memiliki ambang batas risiko yang jauh lebih longgar daripada pendaftaran baru. GMS mengizinkan login akun meskipun `device_key` gagal (fallback header diterima untuk login reguler), asalkan IP tidak masuk daftar hitam spam.

2. **Jika Wajib Mengejar `MEETS_DEVICE_INTEGRITY` di Emulator:**
   * Jangan gunakan image `google_apis_playstore` standar tanpa modifikasi.
   * Gunakan image emulator yang dapat di-root (misal via `rootAVD` atau custom kernel KernelSU-Next).
   * Pasang stack modul: **KernelSU-Next + SUSFS + TEESimulator (JingMatrix) + PlayIntegrityFork**.
   * Dapatkan private OEM `keybox.xml` yang lolos pengecekan `https://android.googleapis.com/attestation/status`.
   * Konfigurasikan target TEESimulator dalam mode **GENERATE** (`com.google.android.gms!`).

3. **Siklus Rotasi Identitas Emulator:**
   * Saat melakukan wipe data emulator untuk pergantian identitas:
     1. Hapus database GSF: `rm -f /data/data/com.google.android.gsf/databases/gservices.db`.
     2. Hapus cache GMS: `pm clear com.google.android.gms`.
     3. Acak nilai SSAID (`settings put secure android_id <random_hex_16>`).
     4. Cold reboot emulator untuk memicu anonymous check-in baru dan menghasilkan GSF Android ID baru.

---

## REFERENSI SUMBER & DOKUMENTASI

1. **Google Play Integrity API Improvements (Android 13+):**  
   https://developer.android.com/google/play/integrity/improvements
2. **Google Key Attestation Verification & Revocation:**  
   https://developer.android.com/privacy-and-security/security-key-attestation  
   https://android-developers.googleblog.com/2019/09/trust-but-verify-attestation-with.html
3. **Google Certificate Revocation List (CRL) Endpoint:**  
   https://android.googleapis.com/attestation/status
4. **MicroG GmsCore AppCertManager Implementation:**  
   https://github.com/microg/GmsCore/blob/master/play-services-core/src/main/kotlin/org/microg/gms/auth/appcert/AppCertManager.kt  
   https://github.com/microg/GmsCore/issues/1835
5. **TEESimulator by JingMatrix (Pengganti TrickyStore):**  
   https://github.com/JingMatrix/TEESimulator
6. **AVD Rooted Play Integrity (Resep Emulator Strong Integrity):**  
   https://github.com/tanishmeh/AVD_Rooted_Integrity  
   https://github.com/tanishmeh/AVD_Rooted_Integrity/blob/master/docs/INTEGRITY_CHAIN.md  
   https://github.com/tanishmeh/AVD_Rooted_Integrity/blob/master/docs/REPRODUCTION.md
7. **Osm0sis PlayIntegrityFork (PIFork):**  
   https://github.com/osm0sis/PlayIntegrityFork
8. **Bypassing Android Hardware Attestation (Quarkslab Research 2026):**  
   https://blog.quarkslab.com/bypassing-android-hardware-attestation.html
9. **Android Emulator Detection & Device Signals:**  
   https://devicefarm.io/glossary/android-emulator
10. **Google Play Games on PC Virtual Integrity:**  
    https://developer.android.com/games/playgames/integrity
