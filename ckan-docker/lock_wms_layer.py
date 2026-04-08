import sys
import json

def main():
    try:
        import psycopg2
    except ImportError:
        print("Error: psycopg2 module not found.")
        sys.exit(1)

    # Koneksi ke database
    conn_string = "dbname='ckandb' user='ckandbuser' password='ckandbpassword' host='db'"
    
    print("Menyiapkan sniper untuk mengunci target peta...")
    try:
        conn = psycopg2.connect(conn_string)
        cursor = conn.cursor()

        # Cari semua jendela peta (geo_view) dan ambil nama layernya
        query = """
            SELECT v.id, v.config, r.name 
            FROM resource_view v 
            JOIN resource r ON v.resource_id = r.id 
            WHERE v.view_type = 'geo_view'
        """
        cursor.execute(query)
        views = cursor.fetchall()

        for vid, config, rname in views:
            if not rname:
                continue
            
            # Format JSON dari database
            if isinstance(config, str):
                config_dict = json.loads(config)
            elif config is None:
                config_dict = {}
            else:
                config_dict = config
            
            # SUNTIKKAN KUNCI TARGET KE DALAM PETA
            config_dict['wms_layer'] = rname
            
            # Simpan kembali ke database
            update_query = "UPDATE resource_view SET config = %s WHERE id = %s"
            cursor.execute(update_query, (json.dumps(config_dict), vid))
            print(f"  [LOCKED] Peta dikunci ke target: {rname}")

        conn.commit()
        print("Selesai! Semua peta sekarang sudah mengunci targetnya masing-masing.")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == '__main__':
    main()