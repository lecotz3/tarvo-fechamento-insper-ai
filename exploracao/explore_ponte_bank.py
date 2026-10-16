import pandas as pd, re
pd.set_option('display.width',250)
D='C:/Users/Leonardo/HACKATOn/data/set2026/'
P='C:/Users/Leonardo/AppData/Local/Temp/claude/C--Users-Leonardo-HACKATOn/be8efb50-a225-4538-9bef-3a5db6e07fde/scratchpad/ponte_extract/PonteCambio_Relatorio_TARVO_092026.xlsx'
p=pd.read_excel(P,header=4,dtype={'CNPJ Cliente':str})
p=p[p.iloc[:,0].astype(str).str.startswith('PC-')].copy()
p['cnpj']=p['CNPJ Cliente'].str.replace(r'\D','',regex=True).str.zfill(14)
print('rows',len(p),'sum spread all', round(p['Spread R$'].sum(),2), 'sum excl dup', round(p.drop_duplicates('Nº Operação')['Spread R$'].sum(),2))
print('sum excl dup and neg', round(p.drop_duplicates('Nº Operação').query('`Spread R$`>0')['Spread R$'].sum(),2))
# spread % check: (taxa-ptax)/ptax and spread R$ = valor ME*(taxa-ptax)
p['chk_brl']=(p['Valor ME']*(p['Taxa Cliente']-p['PTAX Ref.'])).round(2)
p['chk_valor']=(p['Valor ME']*p['Taxa Cliente']).round(2)
print('spread brl mismatch', (abs(p.chk_brl-p['Spread R$'])>0.05).sum(), ' valor mismatch', (abs(p.chk_valor-p['Valor R$'])>0.05).sum())
print(p[abs(p.chk_brl-p['Spread R$'])>0.05][['Nº Operação','Cliente','Valor ME','Taxa Cliente','PTAX Ref.','Spread R$','chk_brl']].to_string())
contr={'17217888000111':1.2,'61720397000180':1.6,'14760206000124':1.25,'16181276000153':1.3,'66564512000199':1.4}
p['sp_pct']=(p['Spread %']*100).round(2)
print(p.groupby(['cnpj','Cliente'])['sp_pct'].agg(['min','max','median','count']).to_string())
print(p.groupby(['Data Liquidação']).size().tail(4))
u=p.drop_duplicates('Nº Operação')
ma=u[u.cnpj=='17217888000111']
base=ma['Valor ME']*ma['PTAX Ref.']
print('Mundo Aberto ops',len(ma),'volume R$',round(ma['Valor R$'].sum(),2),'spread',round(ma['Spread R$'].sum(),2),'div vs 1.2% (ptax base)', round((ma['Spread R$']-base*0.012).sum(),2))
neg=u[u['Spread R$']<0]; print('neg sum', round(neg['Spread R$'].sum(),2), 'estimado', round(neg['Spread Estimado R$ (D-1)'].sum(),2))
print('50% share excl dup', round(u['Spread R$'].sum()/2,2))
