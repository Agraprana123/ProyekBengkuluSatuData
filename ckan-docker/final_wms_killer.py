import sys

def main():
    try:
        import psycopg2
    except ImportError:
        print("Error: psycopg2 module not found.")
        sys.exit(1)

    conn_string = "dbname='ckandb' user='ckandbuser' password='ckandbpassword' host='db'"
    
    print("Memulai operasi isolasi peta (Virtual Service Geoserver)...")
    try:
        conn = psycopg2.connect(conn_string)
        cursor = conn.cursor()

        # Ambil semua data WMS
        cursor.execute("SELECT id, url, name FROM resource WHERE format ILIKE 'wms'")
        resources = cursor.fetchall()

        for res_id, url, name in resources:
            if not name or ':' not in name:
                continue

            # Pisahkan workspace (palapa) dan nama layernya
            workspace, layer_name = name.split(':')

            # BENTUK URL VIRTUAL SERVICE BARU YANG SANGAT SPESIFIK
            # Contoh: https://geo.../geoserver/palapa/pola_ruang_provbkl/wms
            base_domain = "https://geo.bengkuluprov.go.id"
            new_url = f"{base_domain}/geoserver/{workspace}/{layer_name}/wms"
            
            # Timpa ke database
            cursor.execute("UPDATE resource SET url = %s WHERE id = %s", (new_url, res_id))
            print(f"  [TERKUNCI MATI] {name} -> {new_url}")

        conn.commit()
        print("Selesai! Peta sekarang terisolasi dan dipaksa cerdas.")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == '__main__':
    main()