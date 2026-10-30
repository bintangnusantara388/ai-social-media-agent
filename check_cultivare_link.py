"""
Cultivare Auto-Link & Setup Tool
Checks if Facebook Page 'Cultivare.Idea' is linked to Instagram @cultivaree_.
Once linked, automatically retrieves Instagram Business ID and updates .env.
"""

import sys
import re
import requests
from config import BASE_DIR

# Windows UTF-8 fix
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

USER_TOKEN = "EAAPwP9ZCQsSUBS2YIJAcltnXT1bSI7KuKKnZCRIgqb1Xt185yYVLZB10gni84JDNf551NZAsiJnyvPcCwvdt2txSRxZAI53ZAW4fqgZBIJJPt8312h5D2eOW1bgDG8IBLQcDW4P6fC8P6iPVPOZBxpH5oTG9pyhKty3PLAMZCx7wNdeguMWOAbZAtIwduroGLUaDpt4K0whPqNprsYiG3SpdI46sgIWqjvsqZCbo8QPMo29Qeqi7WsWuMOFbbLPZCPmCgq4OYobAGUeysHhzbKMWLW10xwZDZD"
PAGE_ID = "1164601223394079"
PAGE_NAME = "Cultivare.Idea"


def check_and_setup_cultivare():
    print("=" * 65)
    print("🔍 MEMERIKSA STATUS TAUTAN INSTAGRAM CULTIVARE (@cultivaree_)")
    print("=" * 65)

    # 1. Check Page Token
    res_page = requests.get(f"https://graph.facebook.com/v19.0/me/accounts?access_token={USER_TOKEN}")
    if res_page.status_code != 200:
        print(f"❌ Token tidak valid atau kedaluwarsa: {res_page.text}")
        return False

    pages = res_page.json().get("data", [])
    if not pages:
        print("❌ Tidak ditemukan Halaman Facebook pada akun ini.")
        return False

    page = pages[0]
    page_id = page.get("id")
    page_name = page.get("name")
    page_token = page.get("access_token")

    print(f"✅ Halaman Facebook Ditemukan : {page_name} (ID: {page_id})")

    # 2. Query Instagram Business Account
    url = f"https://graph.facebook.com/v19.0/{page_id}?fields=instagram_business_account{{id,username,name}}&access_token={page_token}"
    res = requests.get(url)
    data = res.json()

    ig_data = data.get("instagram_business_account")

    if not ig_data:
        print("\n⚠️ PERHATIAN: Akun Instagram @cultivaree_ BELUM DITAUTKAN ke Halaman Facebook ini!")
        print(f"   Halaman Facebook '{page_name}' saat ini belum memiliki akun Instagram bisnis yang terhubung.")
        print("\n📌 LANGKAH MUDAH MENGHUBUNGKANNYA (Pilih salah satu):")
        print("   Cara 1 (Lewat HP - 1 Menit):")
        print("   1. Buka aplikasi Instagram di HP (login ke @cultivaree_).")
        print("   2. Klik 'Edit Profil' > cari baris 'Halaman' (Page).")
        print(f"   3. Pilih Halaman Facebook '{page_name}'.")
        print("   4. Klik Selesai / Konfirmasi.")
        print("\n   Cara 2 (Lewat Web Facebook):")
        print(f"   1. Buka Halaman Facebook Anda: https://www.facebook.com/{page_id}")
        print("   2. Masuk ke Pengaturan (Settings) > Akun Tertaut (Linked Accounts) > Instagram.")
        print("   3. Klik 'Hubungkan Akun' (Connect Account) lalu login ke @cultivaree_.")
        print("\nSetelah ditautkan, jalankan kembali script ini untuk otomatis menyimpan ID!")
        return False

    ig_id = ig_data.get("id")
    ig_username = ig_data.get("username")
    ig_name = ig_data.get("name")

    print(f"\n🎉 AKUN INSTAGRAM BISNIS BERHASIL DITEMUKAN!")
    print(f"   • Username : @{ig_username}")
    print(f"   • Nama     : {ig_name}")
    print(f"   • ID Meta  : {ig_id}")

    # 3. Update .env file
    env_file = BASE_DIR / ".env"
    if env_file.exists():
        content = env_file.read_text(encoding="utf-8")
        
        # Replace or update
        content = re.sub(r"CULTIVARE_INSTAGRAM_ACCOUNT_ID=.*", f"CULTIVARE_INSTAGRAM_ACCOUNT_ID={ig_id}", content)
        content = re.sub(r"CULTIVARE_INSTAGRAM_ACCESS_TOKEN=.*", f"CULTIVARE_INSTAGRAM_ACCESS_TOKEN={page_token}", content)

        env_file.write_text(content, encoding="utf-8")
        print("\n✅ File .env berhasil diperbarui secara otomatis dengan ID dan Token Cultivare!")
        print("   Akun Cultivare sekarang 100% siap mempublikasikan postingan live.")

    return True


if __name__ == "__main__":
    check_and_setup_cultivare()
