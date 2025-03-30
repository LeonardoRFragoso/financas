"""
Módulo responsável pelas operações de banco de dados das metas financeiras.
"""
import sqlite3
from datetime import datetime
from typing import Dict, List, Optional

DB_PATH = 'financas.db'  # Ajustando para o mesmo nome usado em db.py

def init_goals_table():
    """Inicializa a tabela de metas no banco de dados."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS goals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        description TEXT,
        target_amount REAL NOT NULL,
        current_amount REAL DEFAULT 0,
        deadline DATE,
        category TEXT,
        status TEXT DEFAULT 'Em Andamento',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    conn.commit()
    conn.close()

def add_goal(goal_data: Dict) -> int:
    """Adiciona uma nova meta ao banco de dados."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute('''INSERT INTO goals (
        title, description, target_amount, current_amount, 
        deadline, category, status
    ) VALUES (?, ?, ?, ?, ?, ?, ?)''', (
        goal_data['title'],
        goal_data.get('description', ''),
        goal_data['target_amount'],
        goal_data.get('current_amount', 0),
        goal_data.get('deadline'),
        goal_data.get('category'),
        goal_data.get('status', 'Em Andamento')
    ))
    
    goal_id = c.lastrowid
    conn.commit()
    conn.close()
    return goal_id

def update_goal(goal_id: int, goal_data: Dict) -> bool:
    """Atualiza uma meta existente."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Construir a query de atualização dinamicamente
    update_fields = []
    values = []
    for key, value in goal_data.items():
        if key not in ['id', 'created_at']:
            update_fields.append(f"{key} = ?")
            values.append(value)
    
    # Adicionar updated_at
    update_fields.append("updated_at = CURRENT_TIMESTAMP")
    
    # Montar e executar a query
    query = f"UPDATE goals SET {', '.join(update_fields)} WHERE id = ?"
    values.append(goal_id)
    
    c.execute(query, values)
    success = c.rowcount > 0
    
    conn.commit()
    conn.close()
    return success

def delete_goal(goal_id: int) -> bool:
    """Exclui uma meta do banco de dados."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute("DELETE FROM goals WHERE id = ?", (goal_id,))
    success = c.rowcount > 0
    
    conn.commit()
    conn.close()
    return success

def view_goals() -> List[Dict]:
    """Retorna todas as metas cadastradas."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute('''SELECT id, title, description, target_amount, current_amount,
                        deadline, category, status, created_at, updated_at
                 FROM goals ORDER BY created_at DESC''')
    
    goals = []
    for row in c.fetchall():
        goals.append({
            'id': row[0],
            'title': row[1],
            'description': row[2],
            'target_amount': row[3],
            'current_amount': row[4],
            'deadline': row[5],
            'category': row[6],
            'status': row[7],
            'created_at': row[8],
            'updated_at': row[9]
        })
    
    conn.close()
    return goals

def get_goal(goal_id: int) -> Optional[Dict]:
    """Retorna uma meta específica pelo ID."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute('''SELECT id, title, description, target_amount, current_amount,
                        deadline, category, status, created_at, updated_at
                 FROM goals WHERE id = ?''', (goal_id,))
    
    row = c.fetchone()
    if row:
        goal = {
            'id': row[0],
            'title': row[1],
            'description': row[2],
            'target_amount': row[3],
            'current_amount': row[4],
            'deadline': row[5],
            'category': row[6],
            'status': row[7],
            'created_at': row[8],
            'updated_at': row[9]
        }
    else:
        goal = None
    
    conn.close()
    return goal
