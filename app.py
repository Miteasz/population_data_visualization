# Importowanie potrzebnych bibliotek
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import streamlit as st

# Wczytanie danych
countries_and_continents_path = r'C:\Users\Bartl\OneDrive - Collegium Da Vinci\Wizualizacja danych\common\countries_and_continents.csv'
death_rate_path = r'C:\Users\Bartl\OneDrive - Collegium Da Vinci\Wizualizacja danych\death\death rate.xlsx'
population_path = r'C:\Users\Bartl\OneDrive - Collegium Da Vinci\Wizualizacja danych\populacja\populacja.xlsx'
birth_rate_path = r'C:\Users\Bartl\OneDrive - Collegium Da Vinci\Wizualizacja danych\urodzenia\Birth rate.xlsx'

# Wczytanie danych do Pandas DataFrames
countries_and_continents = pd.read_csv(countries_and_continents_path)
death_rate = pd.read_excel(death_rate_path, sheet_name='death_rate')
population = pd.read_excel(population_path, sheet_name='populacja')
# Usuwanie agregacji, pozostawienie tylko nazw krajów
valid_countries = countries_and_continents['Country'].unique()
population = population[population['Country Name'].isin(valid_countries)]
birth_rate = pd.read_excel(birth_rate_path, sheet_name='Birth_rate')

# Przygotowanie danych do wizualizacji
def prepare_data():
    # Możliwe przekształcenia i wstępne przygotowanie danych
    death_rate['Year'] = death_rate['Atrybut']
    population['Year'] = population['Atrybut']
    birth_rate['Year'] = birth_rate['Atrybut']

    # Przywrócenie pierwotnego złączenia danych populacji z danymi o kontynentach po nazwie kraju
    population_with_continent = population.merge(countries_and_continents, 
                                                 left_on='Country Name', 
                                                 right_on='Country', 
                                                 how='inner')
    return population_with_continent

prepared_data = prepare_data()

# Wizualizacje
st.title("Wizualizacja danych demograficznych")

# Wykres liniowy populacji dla każdego kontynentu - interaktywny
st.subheader("Populacja dla każdego kontynentu w poszczególnych latach")
continent_year_data = prepared_data.groupby(['Continent', 'Year'])['Wartość'].sum().reset_index()

# Interaktywna wizualizacja za pomocą Altair
import altair as alt

selected_continent = st.selectbox("Wybierz kontynent, aby zobaczyć szczegóły", options=['Wszystkie'] + list(continent_year_data['Continent'].unique()))

# Suwak do dynamicznej filtracji lat
min_year = int(continent_year_data['Year'].min())
max_year = int(continent_year_data['Year'].max())
selected_year_range = st.slider("Wybierz zakres lat", min_value=min_year, max_value=max_year, value=(min_year, max_year))

# Filtrowanie danych po kontynencie i zakresie lat
filtered_data = continent_year_data[(continent_year_data['Year'] >= selected_year_range[0]) & (continent_year_data['Year'] <= selected_year_range[1])]

if selected_continent != 'Wszystkie':
    filtered_data = filtered_data[filtered_data['Continent'] == selected_continent]

line_chart = alt.Chart(filtered_data).mark_line(point=True).encode(
    x=alt.X('Year:O', title='Rok'),
    y=alt.Y('Wartość:Q', title='Populacja'),
    color='Continent:N',
    tooltip=['Continent', 'Year', 'Wartość']
).properties(
    width=800,
    height=500,
    title='Populacja kontynentów w poszczególnych latach'
).interactive()

st.altair_chart(line_chart)

# Wykres zależny - populacja krajów (top 15)
if selected_continent != 'Wszystkie':
    st.subheader(f"Top 15 krajów dla kontynentu: {selected_continent}")
    top_countries_data = prepared_data[(prepared_data['Continent'] == selected_continent) & 
                                       (prepared_data['Year'] >= selected_year_range[0]) & 
                                       (prepared_data['Year'] <= selected_year_range[1]) & 
                                       (prepared_data['Country Name'].isin(valid_countries))]
else:
    st.subheader("Top 15 krajów na świecie")
    top_countries_data = prepared_data[(prepared_data['Year'] >= selected_year_range[0]) & 
                                       (prepared_data['Year'] <= selected_year_range[1])]

top_countries_data = top_countries_data[~top_countries_data['Country Name'].isin(['World', 'IDA & IBRD total', 'Low & middle income', 'Middle income', 'IBRD only', 'Early-demographic dividend', 'Upper middle income', 'Lower middle income', 'East Asia & Pacific', 'Late-demographic dividend', 'South Asia'])]
top_countries_data = top_countries_data.groupby(['Country Name'])['Wartość'].mean().reset_index()
top_countries_data = top_countries_data.sort_values(by='Wartość', ascending=False).head(15)

bar_chart = alt.Chart(top_countries_data).mark_bar().encode(
    x=alt.X('Wartość:Q', title='Populacja', axis=alt.Axis(format=',.0f')),
    y=alt.Y('Country Name:N', sort='-x', title='Kraj'),
    tooltip=['Country Name', alt.Tooltip('Wartość:Q', format=',.0f')]
).properties(
    width=800,
    height=500,
    title=f'Top 15 krajów {(f"w kontynencie {selected_continent}" if selected_continent != "Wszystkie" else "na świecie")} (populacja)'
)



st.altair_chart(bar_chart)

