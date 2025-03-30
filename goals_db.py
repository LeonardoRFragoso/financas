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
    
    # Garantir que todos os campos obrigatórios estejam presentes
    if not all(key in goal_data for key in ['title', 'target_amount']):
        raise ValueError("Título e valor alvo são obrigatórios")
    
    c.execute('''INSERT INTO goals (
        title, description, target_amount, current_amount, 
        deadline, category, status
    ) VALUES (?, ?, ?, ?, ?, ?, ?)''', (
        goal_data['title'],
        goal_data.get('description', ''),
        float(goal_data['target_amount']),  # Garantir que é float
        float(goal_data.get('current_amount', 0)),  # Garantir que é float
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
    
    # Construir a query de update dinamicamente
    update_fields = []
    values = []
    
    if 'title' in goal_data:
        update_fields.append('title = ?')
        values.append(goal_data['title'])
    
    if 'description' in goal_data:
        update_fields.append('description = ?')
        values.append(goal_data['description'])
    
    if 'target_amount' in goal_data:
        update_fields.append('target_amount = ?')
        values.append(float(goal_data['target_amount']))
    
    if 'current_amount' in goal_data:
        update_fields.append('current_amount = ?')
        values.append(float(goal_data['current_amount']))
    
    if 'deadline' in goal_data:
        update_fields.append('deadline = ?')
        values.append(goal_data['deadline'])
    
    if 'category' in goal_data:
        update_fields.append('category = ?')
        values.append(goal_data['category'])
    
    if 'status' in goal_data:
        update_fields.append('status = ?')
        values.append(goal_data['status'])
    
    update_fields.append('updated_at = CURRENT_TIMESTAMP')
    
    if not update_fields:
        conn.close()
        return False
    
    query = f'''UPDATE goals SET {', '.join(update_fields)}
                WHERE id = ?'''
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
    
    c.execute('DELETE FROM goals WHERE id = ?', (goal_id,))
    success = c.rowcount > 0
    
    conn.commit()
    conn.close()
    return success

def view_goals() -> List[Dict]:
    """Retorna todas as metas cadastradas."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Permite acessar colunas pelo nome
    c = conn.cursor()
    
    try:
        c.execute('''SELECT id, title, description, target_amount, current_amount,
                        deadline, category, status, created_at, updated_at
                    FROM goals ORDER BY created_at DESC''')
        
        # Converter para lista de dicionários
        goals = [dict(row) for row in c.fetchall()]
        
        # Converter valores numéricos para float
        for goal in goals:
            goal['target_amount'] = float(goal['target_amount'])
            goal['current_amount'] = float(goal['current_amount'])
        
        return goals
    
    except Exception as e:
        print(f"Erro ao buscar metas: {str(e)}")
        return []
    
    finally:
        conn.close()

def get_goal(goal_id: int) -> Optional[Dict]:
    """Retorna uma meta específica pelo ID."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    try:
        c.execute('''SELECT id, title, description, target_amount, current_amount,
                        deadline, category, status, created_at, updated_at
                    FROM goals WHERE id = ?''', (goal_id,))
        
        row = c.fetchone()
        if row:
            goal = dict(row)
            goal['target_amount'] = float(goal['target_amount'])
            goal['current_amount'] = float(goal['current_amount'])
            return goal
        
        return None
    
    except Exception as e:
        print(f"Erro ao buscar meta {goal_id}: {str(e)}")
        return None
    
    finally:
        conn.close()
