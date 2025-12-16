import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="Gestão de Vendas PE - Thales",
    page_icon="📈",
    layout="wide"
)

# ==============================================================================
# 🔒 SISTEMA DE SEGURANÇA (LOGIN)
# ==============================================================================
if 'logado' not in st.session_state:
    st.session_state['logado'] = False

def verificar_senha():
    if st.session_state.senha_input == st.secrets["SENHA_ACESSO"]:
        st.session_state['logado'] = True
    else:
        st.error("Senha incorreta.")

if not st.session_state['logado']:
    st.title("🔒 Acesso Restrito - Print Mais")
    st.markdown("Este painel contém dados estratégicos.")
    st.text_input("Digite a senha de acesso:", type="password", key="senha_input", on_change=verificar_senha)
    st.stop() 

# ==============================================================================
# 📂 CARREGAMENTO DOS DADOS (VIA SECRETS)
# ==============================================================================
@st.cache_data
def load_data():
    try:
        # Lê os dados ocultos no cofre do Streamlit
        dados_json = st.secrets["DADOS_VENDAS"]
        data = json.loads(dados_json)
        
        df = pd.DataFrame(data)
        
        # Cálculos Originais
        df['Media_Trimestre_Ant'] = (df['AGO'] + df['SET'] + df['OUT']) / 3
        
        # Regra de Negócio Original
        def get_status(row):
            if row['NOV'] == 0:
                return "Sem Venda"
            elif row['NOV'] > row['Media_Trimestre_Ant'] * 1.1: # 10% acima
                return "Crescimento"
            elif row['NOV'] < row['Media_Trimestre_Ant'] * 0.9: # 10% abaixo
                return "Queda"
            else:
                return "Estável"
                
        df['Status'] = df.apply(get_status, axis=1)
        return df
    except Exception as e:
        st.error(f"Erro ao processar dados: {e}")
        return pd.DataFrame()

df_full = load_data()

# ==============================================================================
# 🎨 ESTILOS VISUAIS
# ==============================================================================
st.markdown("""
<style>
    .stMetric {
        background-color: #f9f9f9;
        padding: 10px;
        border-radius: 5px;
        border-left: 5px solid #1F78B4;
    }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# 🔍 BARRA LATERAL (FILTROS)
# ==============================================================================
st.sidebar.header("🔍 Filtros")

# Filtro de Cidades
cidades_disponiveis = sorted(df_full['Cidade'].unique())
cidades_sel = st.sidebar.multiselect(
    "Selecione as Cidades:",
    options=cidades_disponiveis,
    default=cidades_disponiveis,
    placeholder="Escolha as cidades..."
)

# Filtro de Status
status_disponiveis = sorted(df_full['Status'].unique())
status_sel = st.sidebar.multiselect(
    "Selecione o Status:",
    options=status_disponiveis,
    default=status_disponiveis
)

# Aplicar Filtros
df = df_full[
    (df_full['Cidade'].isin(cidades_sel)) & 
    (df_full['Status'].isin(status_sel))
]

if df.empty:
    st.warning("Nenhum dado encontrado com os filtros selecionados.")
    st.stop()

# ==============================================================================
# 📊 DASHBOARD PRINCIPAL
# ==============================================================================
st.title(" Painel Thales - Pernambuco")
st.markdown(f"**Visão filtrada:** {len(df)} cidades exibidas.")

col1, col2, col3 = st.columns(3)

total_nov = df['NOV'].sum()
total_media = df['Media_Trimestre_Ant'].sum()
variacao = ((total_nov / total_media) - 1) * 100 if total_media > 0 else 0

with col1:
    st.metric("Total Vendas (Novembro)", f"R$ {total_nov:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

with col2:
    st.metric("Média Trimestral (Ago-Out)", f"R$ {total_media:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

with col3:
    st.metric("Variação (Nov vs Média)", f"{variacao:+.1f}%", delta_color="normal")

st.divider()

# --- GRÁFICOS (ABAS ORIGINAIS) ---
tab_ago, tab_set, tab_out, tab_nov, tab_comp = st.tabs([
    " Agosto", " Setembro", " Outubro", " Novembro", " Comparativo (Média vs Nov)"
])

# Função original de plotagem
def plot_bar(df_in, col_val, cor, titulo):
    # Top 15 para não poluir
    df_sorted = df_in.sort_values(col_val, ascending=True).tail(15) 
    fig = px.bar(
        df_sorted, 
        y='Cidade', 
        x=col_val, 
        orientation='h',
        text_auto='.2s',
        title=titulo,
        color_discrete_sequence=[cor]
    )
    fig.update_layout(xaxis_title="Vendas (R$)", yaxis_title=None, height=500)
    return fig

with tab_ago:
    st.plotly_chart(plot_bar(df, 'AGO', '#A6CEE3', 'Vendas de Agosto'), use_container_width=True)

with tab_set:
    st.plotly_chart(plot_bar(df, 'SET', '#1F78B4', 'Vendas de Setembro'), use_container_width=True)

with tab_out:
    st.plotly_chart(plot_bar(df, 'OUT', '#B2DF8A', 'Vendas de Outubro'), use_container_width=True)

with tab_nov:
    st.plotly_chart(plot_bar(df, 'NOV', '#33A02C', 'Vendas de Novembro'), use_container_width=True)

with tab_comp:
    st.subheader("Média (Ago-Out) vs Novembro")
    df_comp = df[['Cidade', 'Media_Trimestre_Ant', 'NOV']].melt(id_vars='Cidade', var_name='Periodo', value_name='Vendas')
    df_comp['Periodo'] = df_comp['Periodo'].map({'Media_Trimestre_Ant': 'Média 3 Meses', 'NOV': 'Novembro'})
    
    fig_comp = px.bar(
        df_comp,
        x='Cidade',
        y='Vendas',
        color='Periodo',
        barmode='group',
        text_auto='.2s',
        color_discrete_map={'Média 3 Meses': '#999999', 'Novembro': '#E31A1C'},
        height=500
    )
    fig_comp.update_layout(xaxis={'categoryorder':'total descending'})
    st.plotly_chart(fig_comp, use_container_width=True)

# ==============================================================================
# 📋 TABELA DETALHADA (COM CORES ORIGINAIS)
# ==============================================================================
st.markdown("###  Dados Detalhados por Status")

def color_status(val):
    color = 'black'
    if val == 'Crescimento':
        color = '#28a745' # Verde
    elif val == 'Queda':
        color = '#dc3545' # Vermelho
    elif val == 'Sem Venda':
        color = '#999999' # Cinza
    elif val == 'Estável':
        color = '#17a2b8' # Azul
    return f'color: {color}; font-weight: bold;'

st.dataframe(
    df[['Cidade', 'Status', 'AGO', 'SET', 'OUT', 'Media_Trimestre_Ant', 'NOV']].style.map(color_status, subset=['Status']),
    column_config={
        "Media_Trimestre_Ant": st.column_config.NumberColumn("Média (3M)", format="R$ %.2f"),
        "AGO": st.column_config.NumberColumn("Agosto", format="R$ %.2f"),
        "SET": st.column_config.NumberColumn("Setembro", format="R$ %.2f"),
        "OUT": st.column_config.NumberColumn("Outubro", format="R$ %.2f"),
        "NOV": st.column_config.NumberColumn("Novembro", format="R$ %.2f"),
    },
    use_container_width=True,
    height=600
)