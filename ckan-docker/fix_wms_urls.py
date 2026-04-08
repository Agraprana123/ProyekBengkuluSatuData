import sys

def main():
    try:
        import psycopg2
    except ImportError:
        print("Error: psycopg2 module not found. Please install it.")
        sys.exit(1)

    # Koneksi sudah disesuaikan dengan .env milikmu
    conn_string = "dbname='ckandb' user='ckandbuser' password='ckandbpassword' host='db'"
    
    print("Mencoba koneksi ke database Bengkulu Satu Data...")
    try:
        conn = psycopg2.connect(conn_string)
        cursor = conn.cursor()
        print("Koneksi sukses!")

        # Mencari URL WMS yang masih "polos"
        search_query = """
            SELECT id, url, name 
            FROM resource 
            WHERE format ILIKE 'wms' 
              AND url NOT LIKE '%layers=%'
        """
        cursor.execute(search_query)
        resources = cursor.fetchall()

        if not resources:
            print("Hebat! Tidak ada URL WMS yang perlu diperbaiki.")
        else:
            print(f"Menemukan {len(resources)} WMS yang rusak. Memulai perbaikan...")
            
            for res_id, res_url, res_name in resources:
                if not res_name:
                    continue

                separator = '&' if '?' in res_url else '?'
                new_url = f"{res_url}{separator}layers={res_name}"
                
                update_query = "UPDATE resource SET url = %s WHERE id = %s"
                cursor.execute(update_query, (new_url, res_id))
                print(f"  [SUCCESS] Diperbarui: {res_name} -> {new_url}")

            conn.commit()
            print("Perbaikan selesai dan disimpan permanen ke dalam database!")

    except Exception as e:
        print(f"Terjadi error: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == '__main__':
    main()