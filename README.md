# GPROMIO

Herramienta personal para GPRO.

## Funciones actuales

- Lee datos públicos del calendario de GPRO Tools.
- Busca circuito por nombre.
- Calcula combustible total y combustible recomendado para Q2.
- Divide estrategia por stints según cantidad de paradas.
- Estima desgaste de neumáticos por stint con un modelo propio inicial.

## Ejecutar local

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Deploy

En Streamlit Cloud:

- Repository: `hmatias8626-debug/GPROMIO`
- Branch: `main`
- Main file path: `app.py`
