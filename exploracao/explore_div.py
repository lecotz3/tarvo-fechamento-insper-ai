import pandas as pd, sys
pd.set_option('display.width',250); pd.set_option('display.max_rows',200)
D='C:/Users/Leonardo/HACKATOn/data/set2026/'
df=pd.read_csv(D+'01_orbe_relatorio_comissoes_set2026.csv',sep=';',dtype=str)
num=lambda s: pd.to_numeric(s.str.replace('.','',regex=False).str.replace(',','.',regex=False))
for c in ['valor_bruto','taxa_aplicada_pct','valor_taxa','valor_liquido']: df[c]=num(df[c])
df['dmov']=pd.to_datetime(df.data_movimento,format='%d/%m/%Y')
df['dtv']=pd.to_datetime(df.data_venda_original,format='%d/%m/%Y')
# check valor_taxa == bruto*taxa
df['calc']=(df.valor_bruto*df.taxa_aplicada_pct/100).round(2)
print('valor_taxa mismatch:', (abs(df.calc-df.valor_taxa)>0.011).sum())
print(df[abs(df.calc-df.valor_taxa)>0.011][['id_transacao','nome_estabelecimento','valor_bruto','taxa_aplicada_pct','valor_taxa','calc']].to_string())
print('liquido mismatch:', (abs(df.valor_bruto-df.valor_taxa-df.valor_liquido)>0.011).sum())
# rate table (hand-coded for exploration only)
T={ #EC: (deb,cav,c26,c712,pix,ant)
'1075624862_old':(1.49,2.59,3.19,3.79,0.89,2.10),'1075624862':(1.49,2.19,3.19,3.79,0.89,2.10),
'1043396662':(1.49,2.69,3.19,3.79,0.89,2.10),'1038867654':(1.49,2.59,3.19,3.79,0.89,2.10),
'1074504011':(1.49,2.49,2.99,3.59,0.89,2.10),'1086291869':(1.49,2.69,3.19,3.79,0.89,2.10),
'1058961395':(1.39,2.69,3.19,3.79,0.89,2.10),'1018325654':(1.49,2.69,3.19,3.79,0.89,2.10),
'1066100982':(1.49,2.69,3.19,3.79,0.79,2.10),'1037647039':(1.49,2.49,2.99,3.79,0.89,2.10),
'1020660828':(1.49,2.69,3.19,3.49,0.89,2.10),'1014537966':(1.49,2.59,3.19,3.79,0.89,2.10),
'1041180753':(1.49,2.69,3.19,3.79,0.89,2.10),'1000960410':(1.49,2.59,3.09,3.79,0.89,2.10),
'1064304917':(1.49,2.69,3.19,3.79,0.89,2.10),'1068443135':(1.49,2.69,3.19,3.79,0.89,2.10),
'1087276103':(1.49,2.69,3.19,3.79,0.89,2.10),'1070531381':(1.49,2.69,2.99,3.79,0.89,2.10),
'1023622151':(1.49,2.69,3.19,3.79,0.89,2.10),'1098729012':(1.49,2.69,3.19,3.79,0.89,2.10),
'1043300981':(1.49,2.39,2.89,3.79,0.89,2.10),'1061760196':(1.49,2.69,3.19,3.79,0.89,2.10),
}
def contr(r):
    ec=r.cod_estabelecimento
    if ec not in T: return None
    ref = r.dtv if pd.notna(r.dtv) else r.dmov
    if ec=='1075624862' and ref < pd.Timestamp('2026-09-15'): ec='1075624862_old'
    t=T[ec]
    m=r.modalidade
    if r.tipo_lancamento.startswith(('ANTECIP','REVERSAO')): return t[5]
    if m=='DEBITO': return t[0]
    if m=='CREDITO A VISTA': return t[1]
    if m=='PIX': return t[4]
    if m=='CREDITO PARCELADO': return t[2] if int(r.qtd_parcelas)<=6 else t[3]
df['contr']=df.apply(contr,axis=1)
df['diff_pct']=(df.taxa_aplicada_pct-df.contr).round(4)
df['diff_brl']=(df.valor_bruto*df.diff_pct/100).round(2)
print('no contract:', df.contr.isna().sum(), df[df.contr.isna()].nome_estabelecimento.unique())
d=df[(df.diff_pct.abs()>1e-9)&df.contr.notna()]
print('divergent rows', len(d), 'sum brl', d.diff_brl.sum().round(2))
print(d.groupby(['cod_estabelecimento','modalidade','tipo_lancamento','taxa_aplicada_pct','contr']).agg(n=('id_transacao','count'),brl=('diff_brl','sum')).to_string())
# Bridge around 15/09
b=df[(df.cod_estabelecimento=='1075624862')&(df.modalidade=='CREDITO A VISTA')]
print(b.groupby([b.dmov>=pd.Timestamp('2026-09-15'),'taxa_aplicada_pct']).size())
print(df[df.cod_estabelecimento=='1076801732'].groupby(['modalidade','qtd_parcelas','taxa_aplicada_pct'],dropna=False).size())
r=df[(df.cod_estabelecimento=='1074504011')&(df.tipo_lancamento=='VENDA')&df.modalidade.str.startswith('CREDITO',na=False)]
print(r.groupby(['data_movimento','diff_pct']).size().unstack(fill_value=0).to_string())
print('Comissao bruta (valor_taxa) total:', df.valor_taxa.sum().round(2))
print(df.groupby('tipo_lancamento').valor_taxa.sum())
a=df[df.cod_estabelecimento=='1076801732']; print('Atlas linhas',len(a),'taxa total', round(a.valor_taxa.sum(),2))
rg=d[d.cod_estabelecimento=='1074504011']; print('Rota div', len(rg), round(rg.diff_brl.sum(),2), 'vendas', round(rg[rg.tipo_lancamento=='VENDA'].diff_brl.sum(),2))
