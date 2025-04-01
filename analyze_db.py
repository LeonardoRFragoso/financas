import sqlite3
import json

def get_table_structure(db_path):
    """Retorna a estrutura completa do banco de dados"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Obter todas as tabelas
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    
    db_structure = {}
    
    for table in tables:
        table_name = table[0]
        db_structure[table_name] = {}
        
        # Obter informações das colunas
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()
        
        # Armazenar informações das colunas
        db_structure[table_name]["columns"] = []
        for col in columns:
            col_info = {
                "cid": col[0],
                "name": col[1],
                "type": col[2],
                "notnull": col[3],
                "default_value": col[4],
                "pk": col[5]
            }
            db_structure[table_name]["columns"].append(col_info)
        
        # Obter contagem de registros
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        count = cursor.fetchone()[0]
        db_structure[table_name]["record_count"] = count
    
    conn.close()
    return db_structure

if __name__ == "__main__":
    db_structure = get_table_structure("financas.db")
    print(json.dumps(db_structure, indent=2))
