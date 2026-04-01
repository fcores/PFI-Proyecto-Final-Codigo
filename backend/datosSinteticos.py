import pandas as pd
import numpy as np

def generar_datos_diabetes(n_muestras=1000):
    np.random.seed(42)
    
    # 1. Definir probabilidades de clases
    # 0: Tipo 1, 1: Tipo 2, 2: LADA, 3: MODY, 4: Gestacional
    tipos = np.random.choice([0, 1, 2, 3, 4], size=n_muestras, p=[0.15, 0.60, 0.05, 0.05, 0.15])
    
    data = []
    
    for t in tipos:
        row = {'tipo_diabetes': t}
        
        if t == 0: # Tipo 1 (Autoinmune Juvenil)
            row.update({
                'edad_debut': np.random.randint(4, 25),
                'imc': np.random.normal(21, 3),
                'peptido_c': np.random.uniform(0.1, 0.6), # Muy bajo
                'anticuerpos_gad': 1,
                'hba1c': np.random.uniform(7.5, 12.0),
                'acantosis_nigricans': 0,
                'antecedentes_familiares_mody': 0,
                'embarazo': 0
            })
            
        elif t == 1: # Tipo 2 (Metabólica/Adulto)
            row.update({
                'edad_debut': np.random.randint(35, 80),
                'imc': np.random.normal(32, 5),
                'peptido_c': np.random.uniform(1.5, 4.5), # Alto (Resistencia)
                'anticuerpos_gad': 0,
                'hba1c': np.random.uniform(6.5, 10.0),
                'acantosis_nigricans': np.random.choice([0, 1], p=[0.3, 0.7]),
                'antecedentes_familiares_mody': 0,
                'embarazo': 0
            })

        elif t == 2: # LADA (Tipo 1 en adultos)
            row.update({
                'edad_debut': np.random.randint(30, 60),
                'imc': np.random.normal(24, 4),
                'peptido_c': np.random.uniform(0.5, 1.2), # Producción residual
                'anticuerpos_gad': 1,
                'hba1c': np.random.uniform(7.0, 11.0),
                'acantosis_nigricans': 0,
                'antecedentes_familiares_mody': 0,
                'embarazo': 0
            })

        elif t == 3: # MODY (Genética)
            row.update({
                'edad_debut': np.random.randint(12, 30),
                'imc': np.random.normal(23, 2),
                'peptido_c': np.random.uniform(1.0, 2.0), # Producción normal/baja
                'anticuerpos_gad': 0,
                'hba1c': np.random.uniform(6.0, 8.5),
                'acantosis_nigricans': 0,
                'antecedentes_familiares_mody': 1,
                'embarazo': 0
            })

        elif t == 4: # Gestacional
            row.update({
                'edad_debut': np.random.randint(20, 45),
                'imc': np.random.normal(28, 4),
                'peptido_c': np.random.uniform(1.2, 3.0),
                'anticuerpos_gad': 0,
                'hba1c': np.random.uniform(5.8, 7.5),
                'acantosis_nigricans': 0,
                'antecedentes_familiares_mody': 0,
                'embarazo': 1
            })
            
        data.append(row)
    
    df = pd.DataFrame(data)
    # Codificar la etiqueta para que sea legible
    mapping = {0: 'Tipo 1', 1: 'Tipo 2', 2: 'LADA', 3: 'MODY', 4: 'Gestacional'}
    df['tipo_diabetes_label'] = df['tipo_diabetes'].map(mapping)
    
    return df

# Generar el dataset
df_diabetes = generar_datos_diabetes(1000)
print(df_diabetes.head(10))