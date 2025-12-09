import sqlite3

def fix_enums():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    
    # Tables to check: project
    # Columns: design_type, package_type, status
    
    # 1. DesignType
    cursor.execute("UPDATE project SET design_type = 'Hierarchical' WHERE design_type = 'hierarchical'")
    cursor.execute("UPDATE project SET design_type = 'Flat' WHERE design_type = 'flat'")
    
    # 2. PackageType
    cursor.execute("UPDATE project SET package_type = 'Flipchip' WHERE package_type = 'flipchip'")
    cursor.execute("UPDATE project SET package_type = 'Wirebond' WHERE package_type = 'wirebond'")
    
    # 3. ProjectStatus
    cursor.execute("UPDATE project SET status = 'Confirmed' WHERE status = 'confirmed'")
    cursor.execute("UPDATE project SET status = 'Draft' WHERE status = 'draft'")
    cursor.execute("UPDATE project SET status = 'Backlog' WHERE status = 'backlog'")
    
    conn.commit()
    print("Enums updated successfully.")
    conn.close()

if __name__ == "__main__":
    fix_enums()
