import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

def init_theme_manager():
    """
    Inicializa o gerenciador de tema.
    Deve ser chamado no início de cada página.
    """
    # Inicializar a configuração de tema se não existir
    if 'use_dark_theme' not in st.session_state:
        st.session_state.use_dark_theme = False
    
    # Aplicar o tema atual usando query params
    apply_theme()

def toggle_theme():
    """
    Alterna entre os temas claro e escuro.
    """
    st.session_state.use_dark_theme = not st.session_state.use_dark_theme
    apply_theme()
    st.rerun()

def apply_theme():
    """
    Aplica o tema atual ao Streamlit usando query params
    """
    # Define o parâmetro de tema na URL usando a versão atualizada
    if st.session_state.get('use_dark_theme', False):
        st.query_params["theme"] = "dark"
    else:
        st.query_params["theme"] = "light"

def get_theme_colors():
    """
    Retorna um dicionário de cores baseado no tema atual.
    """
    if st.session_state.get('use_dark_theme', False):
        return {
            'background': '#1e2126',
            'paper_bgcolor': '#1e2126',
            'font_color': '#fafafa',
            'grid_color': 'rgba(255, 255, 255, 0.1)',
            'revenue_color': '#4CAF50',
            'expense_color': '#EF5350',
            'investment_color': '#42A5F5',
            'colorscale': 'Plasma',
            'accent_color': '#64b5f6',
            'success_color': '#66bb6a',
            'warning_color': '#ffb74d',
            'error_color': '#e57373',
            'neutral_color': '#9e9e9e'
        }
    else:
        return {
            'background': 'white',
            'paper_bgcolor': 'white',
            'font_color': '#262730',
            'grid_color': 'rgba(0, 0, 0, 0.1)',
            'revenue_color': '#4CAF50',
            'expense_color': '#EF5350',
            'investment_color': '#42A5F5',
            'colorscale': 'Viridis',
            'accent_color': '#1e88e5',
            'success_color': '#4caf50',
            'warning_color': '#ff9800',
            'error_color': '#f44336',
            'neutral_color': '#757575'
        }

def theme_config_section():
    """
    Mostra um controle para alternar entre os temas.
    """
    with st.container():
        cols = st.columns([2, 8])
        with cols[0]:
            if st.toggle("Tema escuro", value=st.session_state.get('use_dark_theme', False), key="theme_toggle"):
                if not st.session_state.get('use_dark_theme', False):
                    st.session_state.use_dark_theme = True
                    apply_theme()
                    st.rerun()
            else:
                if st.session_state.get('use_dark_theme', False):
                    st.session_state.use_dark_theme = False
                    apply_theme()
                    st.rerun()

def apply_theme_to_plotly_chart(fig):
    """
    Aplica o tema atual a um gráfico Plotly existente.
    """
    theme_colors = get_theme_colors()
    
    fig.update_layout(
        paper_bgcolor=theme_colors['paper_bgcolor'],
        plot_bgcolor=theme_colors['background'],
        font_color=theme_colors['font_color'],
        xaxis=dict(
            gridcolor=theme_colors['grid_color'],
            tickfont=dict(color=theme_colors['font_color'])
        ),
        yaxis=dict(
            gridcolor=theme_colors['grid_color'],
            tickfont=dict(color=theme_colors['font_color'])
        )
    )
    
    return fig

def create_pie_chart(labels, values, title=""):
    """
    Cria um gráfico de pizza com o tema atual.
    """
    theme_colors = get_theme_colors()
    
    # Define cores personalizadas dependendo do tema
    if theme_colors['colorscale'] == 'Plasma':
        colors = ['#0d0887', '#46039f', '#7201a8', '#9c179e', '#bd3786', '#d8576b', '#ed7953', '#fb9f3a', '#fdca26', '#f0f921']
    else:  # Viridis
        colors = ['#440154', '#482878', '#3e4989', '#31688e', '#26828e', '#1f9e89', '#35b779', '#6ece58', '#b5de2b', '#fde725']
    
    fig = go.Figure(data=[
        go.Pie(
            labels=labels,
            values=values,
            marker=dict(colors=colors)
        )
    ])
    
    fig.update_layout(
        title=title,
        title_font_color=theme_colors['font_color'],
        font_color=theme_colors['font_color'],
        paper_bgcolor=theme_colors['paper_bgcolor'],
        plot_bgcolor=theme_colors['background'],
        legend_font_color=theme_colors['font_color']
    )
    
    return fig

def create_bar_chart(x, y, title=""):
    """
    Cria um gráfico de barras com o tema atual.
    """
    theme_colors = get_theme_colors()
    
    fig = go.Figure(data=[
        go.Bar(
            x=x,
            y=y,
            marker_color=theme_colors['accent_color']
        )
    ])
    
    fig.update_layout(
        title=title,
        title_font_color=theme_colors['font_color'],
        font_color=theme_colors['font_color'],
        paper_bgcolor=theme_colors['paper_bgcolor'],
        plot_bgcolor=theme_colors['background'],
        xaxis=dict(
            gridcolor=theme_colors['grid_color'],
            tickfont=dict(color=theme_colors['font_color'])
        ),
        yaxis=dict(
            gridcolor=theme_colors['grid_color'],
            tickfont=dict(color=theme_colors['font_color'])
        )
    )
    
    return fig

def style_dataframe(df):
    """
    Estiliza um DataFrame pandas para se adequar ao tema atual.
    Retorna um estilo aplicado ao DataFrame.
    """
    theme_colors = get_theme_colors()
    
    return df.style.set_properties(**{
        'background-color': theme_colors['paper_bgcolor'],
        'color': theme_colors['font_color'],
        'border': f'1px solid {theme_colors["grid_color"]}'
    }).set_table_styles([
        {'selector': 'th', 'props': [
            ('background-color', theme_colors['background']),
            ('color', theme_colors['font_color']),
            ('border', f'1px solid {theme_colors["grid_color"]}'),
            ('padding', '8px')
        ]},
        {'selector': 'tr:hover td', 'props': [
            ('background-color', 'rgba(66, 165, 245, 0.1)')
        ]}
    ])
