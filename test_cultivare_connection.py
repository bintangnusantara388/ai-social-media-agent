"""
Script Verifikasi Koneksi Meta API Akun Cultivare (@cultivaree_)
Jalankan script ini setelah memasukkan ID dan Token Cultivare ke file .env
"""

import sys
import requests
from config import Config

# Windows UTF-8 fix
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

def test_cultivare():
    cfg = Config.get_account_config("cultivare")
    acc_id = cfg.get("instagram_account_id")
    token = cfg.get("instagram_access_token")

    print("=" * 65)
    print("🔍 TESTING KONEKSI META INSTAGRAM: CULTIVARE (@cultivaree_)")
    print("=" * 65)

    if not acc_id:
        print("❌ ERROR: CULTIVARE_INSTAGRAM_ACCOUNT_ID masih kosong di file .env!")
        print("   Silakan ikuti panduan untuk mendapatkan ID Akun Cultivare.")
        return False

    if not token:
        print("❌ ERROR: CULTIVARE_INSTAGRAM_ACCESS_TOKEN masih kosong di file .env!")
        print("   Silakan ikuti panduan untuk mendapatkan Token Meta Cultivare.")
        return False

    print(f"Target Account ID : {acc_id}")
    print(f"Token (Preview)   : {token[:15]}...{token[-8:]}")
    print("\nMenghubungi server Meta Graph API...")

    url = f"https://graph.facebook.com/v19.0/{acc_id}?fields=id,username,name,profile_picture_url&access_token={token}"

    try:
        res = requests.get(url, timeout=15)
        data = res.json()

        if res.status_code == 200 and "username" in data:
            print("\n✅ KONEKSI BERHASIL 100%!")
            print(f"   • Username Instagram : @{data.get('username')}")
            print(f"   • Nama Akun          : {data.get('name')}")
            print(f"   • ID Akun            : {data.get('id')}")
            print("\n🎉 Akun Cultivare siap digunakan untuk publikasi otomatis!")
            return True
        else:
            print(f"\n❌ GAGAL MENGHUBUNGI META (Status Code: {res.status_code})")
            error_msg = data.get("error", {}).get("message", "Unknown error")
            print(f"   Pesan Error: {error_msg}")
            print("\nTips Perbaikan:")
            print("1. Pastikan token memiliki izin: instagram_basic & instagram_content_publish")
            print("2. Pastikan akun Instagram @cultivaree_ sudah ditautkan ke Facebook Page")
            return False

    except Exception as e:
        print(f"\n❌ Terjadi kesalahan jaringan: {e}")
        return False

if __name__ == "__main__":
    test_cultivare()
