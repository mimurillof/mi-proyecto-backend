# %%
import os
import sys
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from scipy.optimize import minimize
import json
from datetime import datetime
from IPython import get_ipython
from IPython.display import Markdown
import streamlit as st

# Habilitar import del proveedor de datos ubicado en la raíz del proyecto
ROOT_DIR = os.path.dirname(os.path.dirname(__file__))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

# Definir el directorio donde se encuentra este script para guardar archivos
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

from client_data_provider import (
    get_client_portfolio,
    fetch_portfolio_market_data,
)

# ==============================================================================
# 1. COLECCIÓN Y PREPARACIÓN DE DATOS
# ==============================================================================

# Portafolio del cliente (placeholder a BD comentado dentro del proveedor)
portfolio_cfg = get_client_portfolio(client_id=None)
tickers = portfolio_cfg["tickers"]
default_weights = portfolio_cfg["weights"]

# Descargar datos históricos via proveedor (unifica con Portfolio_analizer)
print("--- 1. Preparación de Datos (Proveedor) ---")
prices_df, daily_returns = fetch_portfolio_market_data(tickers, period="5y")
print(f"Días descargados: {len(prices_df)} | Activos: {len(tickers)}\n")


# ==============================================================================
# 2. CÁLCULO DE RETORNOS Y MÉTRICAS HISTÓRICAS DEL PORTAFOLIO
# ==============================================================================

# ## Calculate returns
# ### Subtask:
# Calculate the daily returns for each asset in the `data_cleaned` DataFrame.
#
# Select the 'Close' price data
close_prices = prices_df


# ## Calculate portfolio returns
# ### Subtask:
# Calculate the daily returns for a hypothetical portfolio based on the individual asset returns. This will require defining portfolio weights.
#
# Define portfolio weights (desde proveedor; equal-weight por defecto)
portfolio_weights = pd.Series(default_weights).reindex(daily_returns.columns).fillna(0)

# Calculate the weighted daily returns
weighted_daily_returns = daily_returns * portfolio_weights

# Calculate the overall daily portfolio return
portfolio_daily_return = weighted_daily_returns.sum(axis=1)


# ## Calculate wealth index
# ### Subtask:
# Compute the wealth index over time based on the portfolio returns, assuming an initial investment.
#
# Calculate the cumulative return
cumulative_return = (1 + portfolio_daily_return).cumprod()

# Assume an initial investment
initial_investment = 1000

# Calculate the wealth index
wealth_index = initial_investment * cumulative_return


# ## Calculate performance metrics
# ### Subtask:
# Calculate annualized return, annualized volatility, and maximum drawdown for the portfolio.
#
# Calculate annualized return
annualized_return = portfolio_daily_return.mean() * 252

# Calculate annualized volatility
annualized_volatility = portfolio_daily_return.std() * np.sqrt(252)

# Calculate maximum drawdown
# Calculate the peak value
peak = wealth_index.cummax()
# Calculate the drawdown
drawdown = (wealth_index - peak) / peak
# Calculate the maximum drawdown
max_drawdown = drawdown.min()

print("--- 2. Métricas del Portafolio Histórico (Ponderación Igualitaria) ---")
print(f"Annualized Return: {annualized_return:.4f}")
print(f"Annualized Volatility: {annualized_volatility:.4f}")
print(f"Maximum Drawdown: {max_drawdown:.4f}\n")


# ==============================================================================
# 3. SIMULACIÓN DE MONTE CARLO
# ==============================================================================

# ## Define simulation parameters
# ### Subtask:
# Define the number of scenarios, time periods, and initial investment for the simulation.
#
# Define the number of scenarios
n_scenarios = 1000

# Define the number of time periods (trading days)
n_time_periods = portfolio_daily_return.shape[0]

# Define the initial investment
initial_investment = 1000

print("--- 3. Parámetros de Simulación de Monte Carlo ---")
print(f"Number of scenarios: {n_scenarios}")
print(f"Number of time periods: {n_time_periods}")
print(f"Initial investment: {initial_investment}\n")

# ## Calculate portfolio statistics
# ### Subtask:
# Calculate the annualized return and volatility of the historical portfolio data to be used as inputs for the simulation.
#
# Calculate annualized return (mu)
mu = portfolio_daily_return.mean() * 252

# Calculate annualized volatility (sigma)
sigma = portfolio_daily_return.std() * np.sqrt(252)

print("--- Estadísticas para la Simulación ---")
print(f"Annualized Return (mu): {mu:.4f}")
print(f"Annualized Volatility (sigma): {sigma:.4f}\n")

# ## Generate monte carlo simulations
# ### Subtask:
# Use the Geometric Brownian Motion model to generate multiple simulated price paths for the portfolio based on the calculated statistics.
#
# Generate a random walk
daily_random_walk = np.random.standard_normal((n_time_periods, n_scenarios))

# Calculate the daily price changes
# The time step is 1/252 for daily data assuming 252 trading days in a year
daily_changes = np.exp((mu - 0.5 * sigma**2) * (1/252) + sigma * daily_random_walk * np.sqrt(1/252))

# Initialize simulated_prices array
simulated_prices = np.zeros((n_time_periods + 1, n_scenarios))
simulated_prices[0] = initial_investment

# Simulate price paths
for t in range(1, n_time_periods + 1):
    simulated_prices[t] = simulated_prices[t-1] * daily_changes[t-1]

# ## Connect widgets to simulation
# ### Subtask:
# Link the interactive widgets to the simulation function so that the simulation updates dynamically based on user input.
#
def run_simulation(n_scenarios=1000, mu=0.2741, sigma=0.2167):
    """
    Runs a Monte Carlo simulation of portfolio growth using Geometric Brownian Motion
    and visualizes the results using Plotly for interactivity.

    Args:
        n_scenarios (int): The number of simulation scenarios.
        mu (float): The annualized expected return.
        sigma (float): The annualized volatility.
    """
    n_time_periods = portfolio_daily_return.shape[0]
    initial_investment = 1000

    # Generate a random walk
    daily_random_walk = np.random.standard_normal((n_time_periods, n_scenarios))

    # Calculate the daily price changes
    daily_changes = np.exp((mu - 0.5 * sigma**2) * (1/252) + sigma * daily_random_walk * np.sqrt(1/252))

    # Initialize simulated_prices array
    simulated_prices = np.zeros((n_time_periods + 1, n_scenarios))
    simulated_prices[0] = initial_investment

    # Simulate price paths
    for t in range(1, n_time_periods + 1):
        simulated_prices[t] = simulated_prices[t-1] * daily_changes[t-1]

    # Convert to DataFrame for easier handling
    simulated_prices_df = pd.DataFrame(simulated_prices)

    # Calculate key metrics
    terminal_wealth = simulated_prices_df.iloc[-1]
    mean_terminal_wealth = terminal_wealth.mean()
    median_terminal_wealth = terminal_wealth.median()
    std_terminal_wealth = terminal_wealth.std()
    percentile_5 = terminal_wealth.quantile(0.05)
    percentile_95 = terminal_wealth.quantile(0.95)

    # Display key metrics
    print("=" * 50)
    print("SIMULATION METRICS")
    print("=" * 50)
    print(f"Parameters Used:")
    print(f"  • Number of Scenarios: {n_scenarios:,}")
    print(f"  • Expected Return (μ): {mu:.4f}")
    print(f"  • Volatility (σ): {sigma:.4f}")
    print(f"  • Time Periods: {n_time_periods}")
    print("-" * 50)
    print(f"Terminal Wealth Statistics:")
    print(f"  • Mean: ${mean_terminal_wealth:,.2f}")
    print(f"  • Median: ${median_terminal_wealth:,.2f}")
    print(f"  • Std Dev: ${std_terminal_wealth:,.2f}")
    print(f"  • 5th Percentile: ${percentile_5:,.2f}")
    print(f"  • 95th Percentile: ${percentile_95:,.2f}")
    print("=" * 50)

    # Return simulation results for potential use in other cells
    return {
        'simulated_prices_df': simulated_prices_df,
        'terminal_wealth': terminal_wealth,
        'mean_terminal_wealth': mean_terminal_wealth,
        'median_terminal_wealth': median_terminal_wealth,
        'std_terminal_wealth': std_terminal_wealth,
        'percentile_5': percentile_5,
        'percentile_95': percentile_95,
        'n_scenarios': n_scenarios,
        'mu': mu,
        'sigma': sigma,
        'n_time_periods': n_time_periods
    }

# Run simulation with default parameters
simulation_results = run_simulation()


# ## Display simulation metrics
# ### Subtask:
# Display key metrics from the simulation, such as the mean and median of the terminal wealth.
#
# Re-run the simulation to create simulated_prices_df in the global scope
n_time_periods = portfolio_daily_return.shape[0]
initial_investment = 1000

# Generate a random walk
daily_random_walk = np.random.standard_normal((n_time_periods, n_scenarios))

# Calculate the daily price changes
daily_changes = np.exp((mu - 0.5 * sigma**2) * (1/252) + sigma * daily_random_walk * np.sqrt(1/252))

# Initialize simulated_prices array
simulated_prices = np.zeros((n_time_periods + 1, n_scenarios))
simulated_prices[0] = initial_investment

# Simulate price paths
for t in range(1, n_time_periods + 1):
    simulated_prices[t] = simulated_prices[t-1] * daily_changes[t-1]

# Convert to DataFrame for easier handling
simulated_prices_df = pd.DataFrame(simulated_prices)

# Access the terminal wealth values (last row of the DataFrame)
terminal_wealth = simulated_prices_df.iloc[-1]

# Calculate the mean of the terminal wealth values
mean_terminal_wealth = terminal_wealth.mean()

# Calculate the median of the terminal wealth values
median_terminal_wealth = terminal_wealth.median()

print("\n--- Métricas de la Simulación ---")
print(f"Mean Terminal Wealth: {mean_terminal_wealth:.2f}")
print(f"Median Terminal Wealth: {median_terminal_wealth:.2f}\n")


# ==============================================================================
# 4. OPTIMIZACIÓN DE PORTAFOLIOS
# ==============================================================================

# ## Calculate covariance matrix
# ### Subtask:
# Calculate the covariance matrix of the daily asset returns.
#
# Calculate the covariance matrix
cov_matrix = daily_returns.cov()

# ## Define portfolio functions
# ### Subtask:
# Define functions to calculate portfolio return and volatility given a set of weights.
#
# Define the number of trading days in a year
trading_days = 252

def portfolio_return(weights, expected_returns):
    """
    Calculates the annualized portfolio return.

    Args:
        weights (np.ndarray): Array of portfolio weights.
        expected_returns (pd.Series): Daily expected returns for each asset.

    Returns:
        float: Annualized portfolio return.
    """
    return np.dot(weights.T, expected_returns) * trading_days

def portfolio_volatility(weights, annualized_cov_matrix):
    """
    Calculates the portfolio volatility.

    Args:
        weights (np.ndarray): Array of portfolio weights.
        annualized_cov_matrix (pd.DataFrame): Annualized covariance matrix.

    Returns:
        float: Portfolio volatility.
    """
    return np.sqrt(np.dot(weights.T, np.dot(annualized_cov_matrix, weights)))

print("--- 4. Optimización de Portafolios ---")
print("Funciones de retorno y volatilidad del portafolio definidas.\n")

# ## Find gmv portfolio
# ### Subtask:
# Use an optimizer to find the weights for the Global Minimum Volatility (GMV) portfolio.
#
from scipy.optimize import minimize

# Annualize the covariance matrix
annualized_cov_matrix = cov_matrix * trading_days

# Define the objective function to minimize (portfolio volatility)
def objective_function(weights):
    return portfolio_volatility(weights, annualized_cov_matrix)

# Define the constraints
constraints = ({'type': 'eq', 'fun': lambda weights: np.sum(weights) - 1})
bounds = tuple((0, 1) for asset in range(len(daily_returns.columns))) # Weights must be between 0 and 1

# Define the initial guess (equal weights)
initial_weights = np.array([1./len(daily_returns.columns)] * len(daily_returns.columns))

# Run the optimizer
optimization_result = minimize(objective_function, initial_weights, method='SLSQP', bounds=bounds, constraints=constraints)

# Extract the optimal weights for the GMV portfolio
gmv_weights = optimization_result.x

print("Pesos del Portafolio de Mínima Volatilidad Global (GMV):")
print(pd.Series(gmv_weights, index=daily_returns.columns))
print("\n")

# ## Calculate ew portfolio weights
# ### Subtask:
# Calculate the weights for the Equal-Weighted (EW) portfolio.
#
# Equal-Weighted (EW) para comparación
num_assets = daily_returns.shape[1]
equal_weight = 1.0 / num_assets
ew_weights = pd.Series(equal_weight, index=daily_returns.columns)

print("Pesos del Portafolio de Ponderación Equitativa (EW):")
print(ew_weights)
print("\n")

# ## Find msr portfolio
# ### Subtask:
# Use an optimizer to find the weights for the Maximum Sharpe Ratio (MSR) portfolio (this will require estimating expected returns).
#
# Calculate the annualized expected returns for each asset
expected_returns = daily_returns.mean() * trading_days

# Define the negative Sharpe Ratio function to minimize
def negative_sharpe_ratio(weights, expected_returns, annualized_cov_matrix):
    """
    Calculates the negative Sharpe Ratio of a portfolio.

    Args:
        weights (np.ndarray): Array of portfolio weights.
        expected_returns (pd.Series): Annualized expected returns for each asset.
        annualized_cov_matrix (pd.DataFrame): Annualized covariance matrix.

    Returns:
        float: Negative Sharpe Ratio.
    """
    port_return = portfolio_return(weights, expected_returns / trading_days) # Use daily expected returns for portfolio_return function
    port_volatility = portfolio_volatility(weights, annualized_cov_matrix)
    # Avoid division by zero if volatility is zero
    if port_volatility == 0:
        return np.inf
    return -port_return / port_volatility

# Define the constraints (sum of weights is 1, weights are between 0 and 1)
constraints = ({'type': 'eq', 'fun': lambda weights: np.sum(weights) - 1})
bounds = tuple((0, 1) for asset in range(len(daily_returns.columns)))

# Define the initial guess (equal weights)
initial_weights = np.array([1./len(daily_returns.columns)] * len(daily_returns.columns))

# Run the optimizer to find the MSR portfolio weights
optimization_result_msr = minimize(
    negative_sharpe_ratio,
    initial_weights,
    args=(expected_returns, annualized_cov_matrix),
    method='SLSQP',
    bounds=bounds,
    constraints=constraints
)

# Extract the optimal weights for the MSR portfolio
msr_weights = optimization_result_msr.x

print("Pesos del Portafolio de Máximo Ratio de Sharpe (MSR):")
print(pd.Series(msr_weights, index=daily_returns.columns))
print("\n")

# ## Convertir Valores en Dólares del Cliente a Pesos Ponderados
# ### Subtask:
# Take client's dollar-value investments, calculate the total portfolio value, and convert them into percentage weights for analysis.
#
# --- ENTRADA DEL CLIENTE (VALORES EN DÓLARES) ---
# Placeholder: si existiera BD, estos valores vendrían del perfil del cliente.
valores_en_dolares_cliente = {t: 1.0 for t in tickers}  # equiponderado por defecto

# --- CÁLCULO AUTOMÁTICO DE PESOS ---

# 1. Calcular el valor total del portafolio sumando los valores individuales
valor_total_portafolio = sum(valores_en_dolares_cliente.values())

# 2. Calcular el peso de cada activo (valor del activo / valor total del portafolio)
pesos_calculados = {
    ticker: valor / valor_total_portafolio
    for ticker, valor in valores_en_dolares_cliente.items()
}

# 3. Convertir el diccionario a una Serie de pandas, asegurando el orden correcto
#    .reindex() garantiza que el orden de los tickers sea consistente con los otros datos.
#    .fillna(0) asigna un peso de 0 a cualquier ticker que el cliente no posea.
user_portfolio_weights = pd.Series(pesos_calculados).reindex(daily_returns.columns).fillna(0)


# --- VERIFICACIÓN (Resultados que se mostrarán en pantalla) ---
print("--- Portafolio del Cliente ---")
print(f"Valor Total del Portafolio del Cliente: ${valor_total_portafolio:,.2f}")
print("\n" + "="*50)
print("Pesos Porcentuales Calculados Automáticamente:")

# Imprime los pesos en un formato de porcentaje fácil de leer
for ticker, weight in user_portfolio_weights.items():
    if weight > 0: # Solo mostrar activos con peso
        print(f"  - {ticker}: {weight:.2%}")

# Asegurarse de que la suma de los pesos es 100%
print("="*50)
print(f"Suma Total de los Pesos: {user_portfolio_weights.sum():.2%}")
print("\nSerie de Pesos final que se usará para el análisis:")
print(user_portfolio_weights)
print("\n")

# Calcular el rendimiento anualizado del portafolio del cliente
user_portfolio_return = portfolio_return(user_portfolio_weights, expected_returns / trading_days)

# Calcular la volatilidad anualizada del portafolio del cliente
user_portfolio_volatility = portfolio_volatility(user_portfolio_weights, annualized_cov_matrix)

# Mostrar las métricas calculadas
print("Métricas del Portafolio del Cliente:")
print(f"Rendimiento Anualizado Esperado: {user_portfolio_return:.4f}")
print(f"Volatilidad Anualizada: {user_portfolio_volatility:.4f}\n")


# ==============================================================================
# 5. FRONTERA EFICIENTE Y VISUALIZACIÓN
# ==============================================================================

print("--- 5. Visualización de la Frontera Eficiente ---")

# ## Calculate risk and return for efficient frontier
# ### Subtask:
# Calculate the portfolio return and volatility for a range of portfolio weights to trace the Efficient Frontier.
#
def get_efficient_frontier(n_points, expected_returns, annualized_cov_matrix):
    """
    Calculates the efficient frontier for a portfolio.

    Args:
        n_points (int): The number of points to generate on the efficient frontier.
        expected_returns (pd.Series): Annualized expected returns for each asset.
        annualized_cov_matrix (pd.DataFrame): Annualized covariance matrix.

    Returns:
        tuple: A tuple containing two numpy arrays:
               - port_volatilities: Annualized portfolio volatilities for each point on the frontier.
               - port_returns: Annualized portfolio returns (target returns) for each point on the frontier.
    """
    # Initialize arrays to store results
    port_returns = []
    port_volatilities = []

    # Generate a range of target returns
    min_return = expected_returns.min()
    max_return = expected_returns.max()
    target_returns = np.linspace(min_return, max_return, n_points)

    # Define constraints
    constraints_ef = lambda target: (
        {'type': 'eq', 'fun': lambda weights: np.sum(weights) - 1},  # Sum of weights is 1
        {'type': 'eq', 'fun': lambda weights: portfolio_return(weights, expected_returns / trading_days) - target} # Portfolio return equals target return
    )
    bounds = tuple((0, 1) for asset in range(len(expected_returns))) # Weights must be between 0 and 1

    # Define initial guess (equal weights)
    initial_weights = np.array([1./len(expected_returns)] * len(expected_returns))

    # Iterate through target returns and find the minimum volatility portfolio
    for target_return in target_returns:
        # Define the objective function to minimize (portfolio volatility)
        def objective_function(weights):
            return portfolio_volatility(weights, annualized_cov_matrix)

        # Run the optimizer
        optimization_result = minimize(
            objective_function,
            initial_weights,
            method='SLSQP',
            bounds=bounds,
            constraints=constraints_ef(target_return)
        )

        # Store the results if optimization was successful
        if optimization_result.success:
            port_volatilities.append(optimization_result.fun)
            port_returns.append(target_return)

    return np.array(port_volatilities), np.array(port_returns)

# Calculate the efficient frontier with 50 points
print("Calculando la Frontera Eficiente...")
port_volatilities, port_returns = get_efficient_frontier(
    50, expected_returns, annualized_cov_matrix
)
print("Frontera Eficiente calculada.\n")

# Calcular el rendimiento anualizado del portafolio equal-weighted
ew_portfolio_return = portfolio_return(ew_weights, expected_returns / trading_days)
ew_portfolio_volatility = portfolio_volatility(ew_weights, annualized_cov_matrix)

# Calcular el rendimiento anualizado del portafolio GMV
gmv_portfolio_return = portfolio_return(gmv_weights, expected_returns / trading_days)
gmv_portfolio_volatility = portfolio_volatility(gmv_weights, annualized_cov_matrix)

# Calcular el rendimiento anualizado del portafolio MSR
msr_portfolio_return = portfolio_return(msr_weights, expected_returns / trading_days)
msr_portfolio_volatility = portfolio_volatility(msr_weights, annualized_cov_matrix)

# Define a risk-free rate
risk_free_rate = 0.01

# Calculate the slope of the CML
cml_slope = (msr_portfolio_return - risk_free_rate) / msr_portfolio_volatility

# Generate a range of volatility values for the CML
cml_volatilities = np.linspace(0, max(port_volatilities) * 1.1, 100) # Extend slightly beyond max portfolio volatility

# Calculate the corresponding return values for the CML
cml_returns = risk_free_rate + cml_slope * cml_volatilities


# --- Creación de Gráficos Interactivos ---
print("🚀 Creando el Dashboard de Análisis de Portafolio...")
print("=" * 60)

# 1. Gráfico de Crecimiento del Portafolio
fig_growth = go.Figure()
fig_growth.add_trace(go.Scatter(
    x=wealth_index.index,
    y=wealth_index.values,
    mode='lines',
    name='Portfolio Value',
    line=dict(width=3, color='#1f77b4'),
    hovertemplate='<b>Date:</b> %{x}<br><b>Value:</b> $%{y:,.2f}<extra></extra>'
))

ann_return = (wealth_index.iloc[-1] / wealth_index.iloc[0]) ** (252 / len(wealth_index)) - 1
ann_volatility = portfolio_daily_return.std() * np.sqrt(252)

fig_growth.add_annotation(
    x=0.02, y=0.98, xref="paper", yref="paper",
    text=f"<b>Key Metrics:</b><br>Annualized Return: {ann_return:.2%}<br>Annualized Volatility: {ann_volatility:.2%}<br>Max Drawdown: {max_drawdown:.2%}",
    showarrow=False,
    font=dict(size=12, color="white"),
    bgcolor="rgba(0,0,0,0.8)",
    bordercolor="white",
    borderwidth=1
)

fig_growth.update_layout(
    title='📈 Crecimiento del Portafolio a lo Largo del Tiempo (Dashboard Interactivo)',
    xaxis_title='Fecha',
    yaxis_title='Valor del Portafolio ($)',
    hovermode='x unified',
    template='plotly_white',
    height=600,
    width=1000
)

# 2. Gráfico de la Frontera Eficiente
fig_ef = go.Figure()

fig_ef.add_trace(go.Scatter(
    x=port_volatilities,
    y=port_returns,
    mode='markers',
    name='Frontera Eficiente',
    marker=dict(size=8, color='lightblue', opacity=0.8),
    hovertemplate='<b>Frontera Eficiente</b><br>Volatilidad: %{x:.3f}<br>Retorno: %{y:.3f}<extra></extra>'
))

portfolios_to_plot = [
    (ew_portfolio_volatility, ew_portfolio_return, 'Ponderación Equitativa', 'red', '⭐', 'star'),
    (gmv_portfolio_volatility, gmv_portfolio_return, 'Portafolio GMV', 'green', '🛡️', 'star'),
    (msr_portfolio_volatility, msr_portfolio_return, 'Portafolio MSR', 'purple', '🎯', 'star'),
    (user_portfolio_volatility, user_portfolio_return, 'Portafolio del Cliente', 'blue', '💎', 'diamond')
]

for vol, ret, name, color, emoji, symbol in portfolios_to_plot:
    fig_ef.add_trace(go.Scatter(
        x=[vol], y=[ret],
        mode='markers+text',
        name=f'{emoji} {name}',
        marker=dict(size=20, color=color, symbol=symbol),
        text=[emoji],
        textposition="middle center",
        textfont=dict(size=16),
        hovertemplate=f'<b>{name}</b><br>Volatilidad: %{{x:.3f}}<br>Retorno: %{{y:.3f}}<extra></extra>'
    ))

fig_ef.add_trace(go.Scatter(
    x=cml_volatilities,
    y=cml_returns,
    mode='lines',
    name='📊 Línea del Mercado de Capitales (CML)',
    line=dict(width=3, color='orange', dash='dash'),
    hovertemplate='<b>CML</b><br>Volatilidad: %{x:.3f}<br>Retorno: %{y:.3f}<extra></extra>'
))

fig_ef.update_layout(
    title='🎯 Análisis de la Frontera Eficiente (Interactivo)',
    xaxis_title='Volatilidad Anualizada',
    yaxis_title='Retorno Anualizado',
    template='plotly_white',
    height=700,
    width=1100
)

# Mostrar gráficos
print("📊 Mostrando Gráfico de Crecimiento del Portafolio Interactivo...")
fig_growth.show()

print("\n🎯 Mostrando Frontera Eficiente Interactiva...")
fig_ef.show()

# Guardar gráficos en archivos
fig_growth.write_html(os.path.join(SCRIPT_DIR, "portfolio_growth_interactive.html"))
fig_ef.write_html(os.path.join(SCRIPT_DIR, "efficient_frontier_interactive.html"))
fig_growth.write_image(os.path.join(SCRIPT_DIR, "portfolio_growth.png"), width=1000, height=600)
fig_ef.write_image(os.path.join(SCRIPT_DIR, "efficient_frontier.png"), width=1100, height=700)

print("\n✅ Creación del Dashboard Completa!")
print("=" * 60)
print("📁 Archivos Generados:")
print("   • portfolio_growth_interactive.html")
print("   • efficient_frontier_interactive.html")
print("   • portfolio_growth.png")
print("   • efficient_frontier.png\n")


# ==============================================================================
# 6. VISUALIZACIONES AVANZADAS (STREAMLIT Y TREEMAP)
# ==============================================================================

def run_simulation_streamlit(n_scenarios, mu, sigma):
    """
    Runs a Monte Carlo simulation of portfolio growth using Geometric Brownian Motion
    and visualizes the results using Plotly with improved hover and PNG export.

    Args:
        n_scenarios (int): The number of simulation scenarios.
        mu (float): The annualized expected return.
        sigma (float): The annualized volatility.
    """
    n_time_periods = portfolio_daily_return.shape[0]
    initial_investment = 1000

    daily_random_walk = np.random.standard_normal((n_time_periods, n_scenarios))
    daily_changes = np.exp((mu - 0.5 * sigma**2) * (1/252) + sigma * daily_random_walk * np.sqrt(1/252))
    simulated_prices = np.zeros((n_time_periods + 1, n_scenarios))
    simulated_prices[0] = initial_investment

    for t in range(1, n_time_periods + 1):
        simulated_prices[t] = simulated_prices[t-1] * daily_changes[t-1]

    simulated_prices_df = pd.DataFrame(simulated_prices)
    fig_trajectories = go.Figure()
    
    sample_size = min(50, n_scenarios)
    sample_indices = np.random.choice(n_scenarios, sample_size, replace=False)
    
    for i in sample_indices:
        fig_trajectories.add_trace(go.Scatter(
            y=simulated_prices_df.iloc[:, i], mode='lines',
            line=dict(width=1, color='rgba(100,149,237,0.3)'),
            showlegend=False, hovertemplate='T%{x}: $%{y:,.0f}<extra></extra>', name=f'Path {i+1}'
        ))
    
    mean_trajectory = simulated_prices_df.mean(axis=1)
    fig_trajectories.add_trace(go.Scatter(
        y=mean_trajectory, mode='lines', line=dict(width=4, color='#FF4B4B', dash='solid'),
        name='Mean Path', hovertemplate='<b>Mean</b><br>T%{x}: $%{y:,.0f}<extra></extra>'
    ))
    
    final_mean = mean_trajectory.iloc[-1]
    fig_trajectories.add_annotation(
        x=0.02, y=0.98, xref="paper", yref="paper",
        text=f"<b>Quick Stats</b><br>Scenarios: {n_scenarios:,}<br>Final Mean: ${final_mean:,.0f}<br>μ: {mu:.1%} | σ: {sigma:.1%}",
        showarrow=False, bgcolor="rgba(255,255,255,0.9)", bordercolor="rgba(0,0,0,0.2)",
        borderwidth=1, font=dict(size=10, color="black"), align="left"
    )
    
    fig_trajectories.update_layout(
        title={'text': '🚀 Monte Carlo Portfolio Trajectories', 'x': 0.5, 'font': {'size': 18}},
        xaxis_title='Time Periods', yaxis_title='Portfolio Value ($)', template='plotly_white',
        height=600, width=1000, hovermode='x unified', hoverdistance=20
    )

    terminal_wealth_sim = simulated_prices_df.iloc[-1]
    fig_histogram = go.Figure()
    fig_histogram.add_trace(go.Histogram(
        x=terminal_wealth_sim, nbinsx=50, marker=dict(color='skyblue', line=dict(color='navy', width=1)),
        hovertemplate='$%{x:,.0f}<br>Count: %{y}<extra></extra>', name='Distribution'
    ))
    
    mean_terminal = terminal_wealth_sim.mean()
    median_terminal = terminal_wealth_sim.median()
    percentile_5 = np.percentile(terminal_wealth_sim, 5)
    
    for value, color, name in [(mean_terminal, "#FF4B4B", "Mean"), (median_terminal, "#00CC44", "Median"), (percentile_5, "#FF8C00", "5th %")]:
        fig_histogram.add_vline(x=value, line_dash="dash", line_color=color, line_width=2,
                                annotation_text=f"{name}: ${value:,.0f}", annotation_position="top", annotation_font_size=9)
    
    fig_histogram.update_layout(
        title={'text': '📊 Terminal Wealth Distribution', 'x': 0.5, 'font': {'size': 18}},
        xaxis_title='Terminal Wealth ($)', yaxis_title='Frequency', template='plotly_white',
        height=500, width=900, showlegend=False
    )
    
    try:
        fig_trajectories.write_image(os.path.join(SCRIPT_DIR, 'monte_carlo_trajectories.png'), width=1000, height=600, scale=2)
        fig_histogram.write_image(os.path.join(SCRIPT_DIR, 'monte_carlo_distribution.png'), width=900, height=500, scale=2)
        print("\n💾 Imágenes de alta resolución de Monte Carlo exportadas.")
    except Exception as e:
        print(f"\n⚠️ Falló la exportación de Monte Carlo a PNG: {e}")

    fig_trajectories.write_html(os.path.join(SCRIPT_DIR, 'monte_carlo_trajectories.html'))
    fig_histogram.write_html(os.path.join(SCRIPT_DIR, 'monte_carlo_distribution.html'))
    
    fig_trajectories.show()
    fig_histogram.show()

# Nota: La siguiente línea ejecutará la simulación y mostrará/guardará los gráficos.
# No se requiere streamlit para esta parte.
print("\n--- 6. Visualizaciones Avanzadas ---")
print("🎮 Ejecutando simulación mejorada y guardando resultados...")
run_simulation_streamlit(n_scenarios, mu, sigma)


# ==============================================================================
# 6. VISUALIZACIONES AVANZADAS (TREEMAP - CÓDIGO ORIGINAL DEL USUARIO)
# ==============================================================================

def generar_treemap_original():
    """
    Genera el Treemap utilizando la lógica y estilo EXACTOS del script original del usuario.
    Esta función asume que las variables `msr_weights`, `tickers`, y `expected_returns`
    han sido calculadas y existen en el ámbito global del script.
    """
    print("\n" + "="*60)
    print("📊 Generando Treemap del Portafolio MSR con datos reales (Lógica Original)")
    print("="*60)

    try:
        # 1. VERIFICAR Y ACCEDER A LAS VARIABLES GLOBALES REQUERIDAS
        if 'msr_weights' not in globals() or 'tickers' not in globals() or 'expected_returns' not in globals():
            print("❌ No se encontraron las variables necesarias del portafolio MSR.")
            print("💡 Asegúrate de que las secciones anteriores del script se hayan ejecutado correctamente.")
            return

        # Accede directamente a las variables globales que ya fueron calculadas
        msr_weights = globals()['msr_weights']
        tickers = globals()['tickers']
        expected_returns = globals()['expected_returns']

        print(f"✅ Variables encontradas y listas para usar.")

        # --- A PARTIR DE AQUÍ, EL CÓDIGO ES IDÉNTICO AL ORIGINAL ---

        # 2. FILTRAR ACTIVOS CON PESO SIGNIFICATIVO (>0.5%)
        significant_assets = []
        for i, (ticker, weight) in enumerate(zip(tickers, msr_weights)):
            if weight > 0.005:
                if isinstance(expected_returns, pd.Series):
                    exp_return = expected_returns.iloc[i] if i < len(expected_returns) else 0.10
                else:
                    exp_return = expected_returns[i] if i < len(expected_returns) else 0.10
                significant_assets.append({'ticker': ticker, 'weight': weight, 'expected_return': exp_return})
        
        print(f"🎯 Activos significativos encontrados: {len(significant_assets)}")

        # 3. OBTENER INFORMACIÓN DE SECTORES USANDO YAHOO FINANCE
        print("\n🔍 Obteniendo información de sectores desde Yahoo Finance...")
        portfolio_data = []
        for asset in significant_assets:
            ticker_symbol = asset['ticker']
            try:
                ticker_obj = yf.Ticker(ticker_symbol)
                info = ticker_obj.info
                sector = info.get('sector', 'N/A')
                name = info.get('shortName', ticker_symbol)
                if sector == 'N/A':
                    if any(crypto in ticker_symbol.upper() for crypto in ['BTC', 'ETH', 'PAXG']): sector = 'Criptoactivos'
                    elif any(bond in ticker_symbol.upper() for bond in ['TLT', 'IEF', 'MBB']): sector = 'Bonos'
                    else: sector = 'Otros'
                portfolio_data.append({'ticker': ticker_symbol, 'name': name, 'sector': sector, 'weight': asset['weight'], 'expected_return': asset['expected_return']})
            except Exception as e:
                print(f"      ⚠️ Error con {ticker_symbol}, usando fallback manual.")
                if any(crypto in ticker_symbol.upper() for crypto in ['BTC', 'ETH', 'PAXG']): sector = 'Criptoactivos'
                elif any(bond in ticker_symbol.upper() for bond in ['TLT', 'IEF', 'MBB']): sector = 'Bonos'
                elif ticker_symbol in ['NVDA', 'GOOG', 'GOOGL', 'AAPL']: sector = 'Technology'
                else: sector = 'Otros'
                portfolio_data.append({'ticker': ticker_symbol, 'name': ticker_symbol, 'sector': sector, 'weight': asset['weight'], 'expected_return': asset['expected_return']})
        
        # 4. CREAR DATAFRAME Y AGRUPAR POR SECTORES
        df = pd.DataFrame(portfolio_data)
        sector_summary = df.groupby('sector').agg({'weight': 'sum', 'expected_return': 'mean'}).round(4)
        print("\n📈 Resumen por sectores:")
        print(sector_summary)

        # 5. PREPARAR DATOS PARA TREEMAP JERÁRQUICO
        sectors = df['sector'].unique()
        sector_weights = df.groupby('sector')['weight'].sum()
        sector_returns = df.groupby('sector')['expected_return'].mean()
        ids = ['Portafolio MSR'] + sectors.tolist() + df['ticker'].tolist()
        labels = ['Portafolio MSR'] + sectors.tolist() + [f"{row['name']} ({row['ticker']})" for _, row in df.iterrows()]
        parents = [''] + ['Portafolio MSR'] * len(sectors) + df['sector'].tolist()
        values = [df['weight'].sum()] + sector_weights.tolist() + df['weight'].tolist()
        total_return = sum(df['weight'] * df['expected_return'])
        contribution = [total_return] + [sector_weights.get(s, 0) * sector_returns.get(s, 0) for s in sectors] + [row['weight'] * row['expected_return'] for _, row in df.iterrows()]
        
        # 6. SISTEMA DE COLORES BASADO EN CONTRIBUCIÓN (REFINADO)
        colors = []
        for contrib in contribution:
            if contrib > 0.25: colors.append('rgba(22, 163, 74, 0.9)')
            elif contrib > 0.15: colors.append('rgba(34, 197, 94, 0.8)')
            elif contrib > 0.05: colors.append('rgba(74, 222, 128, 0.8)')
            elif contrib > 0: colors.append('rgba(134, 239, 172, 0.8)')
            elif contrib < -0.1: colors.append('rgba(239, 68, 68, 0.8)')
            elif contrib < 0: colors.append('rgba(252, 165, 165, 0.8)')
            else: colors.append('rgba(156, 163, 175, 0.8)')
        if colors: colors[0] = 'rgba(107, 114, 128, 0.8)'

        # 7. CREAR TREEMAP INTERACTIVO
        fig = go.Figure(go.Treemap(
            ids=ids, labels=labels, parents=parents, values=[v * 100 for v in values],
            text=[f"Contribución: {c*100:.2f}%" for c in contribution],
            textinfo="label+value",
            hovertemplate='<b>%{label}</b><br>Peso: %{value:.1f}%<br>%{text}<extra></extra>',
            pathbar={'visible': True},
            marker={'colors': colors, 'line': {'width': 1, 'color': '#fff'}},
            branchvalues='total', tiling={'packing': 'squarify'}
        ))

        # 8. CONFIGURAR LAYOUT
        fig.update_layout(
            title={'text': "📊 Composición del Portafolio MSR - Análisis Detallado", 'x': 0.5, 'font': {'size': 16}},
            margin={'t': 50, 'l': 10, 'r': 10, 'b': 10}, autosize=True,
            paper_bgcolor='#FFFFFF', plot_bgcolor='#FFFFFF', font={'color': '#374151'}, height=500
        )

        # 9. MOSTRAR GRÁFICO
        print("\n🎨 Mostrando Treemap del Portafolio MSR (Estilo Original)...")
        fig.show()

        # 10. EXPORTAR GRÁFICOS
        try:
            fig.write_image(os.path.join(SCRIPT_DIR, 'msr_portfolio_treemap_original.png'), width=1000, height=600, scale=2)
            print("\n💾 Imagen de alta resolución exportada: msr_portfolio_treemap_original.png")
            fig.write_html(os.path.join(SCRIPT_DIR, 'msr_portfolio_treemap_original.html'))
            print("📱 Archivo HTML interactivo guardado: msr_portfolio_treemap_original.html")
        except Exception as e:
            print(f"\n⚠️ Falló la exportación a PNG o HTML: {e}")
            print("   (Para exportar a PNG, asegúrate de tener `kaleido` instalado: pip install kaleido)")
        
    except Exception as e:
        import traceback
        print(f"❌ Error durante la generación del Treemap original: {e}")
        print("🔧 Detalles del error:")
        print(traceback.format_exc())

# --- Llama a la función para ejecutarla ---
generar_treemap_original()


# ==============================================================================
# 7. GENERACIÓN DE REPORTES Y EXPORTACIÓN DE RESULTADOS
# ==============================================================================

def generar_informe_financiero_completo():
    """
    Genera, muestra y GUARDA un informe financiero detallado en formato Markdown.
    """
    try:
        if 'daily_returns' not in globals() or 'gmv_weights' not in globals():
            print("⚠️ Error: Variables no encontradas. Ejecuta el script completo.")
            return
    except NameError as e:
        print(f"⚠️ Error: {e}")
        return

    reporte_md = f"# 📈 Reporte de Análisis Exhaustivo de Portafolio\n\n"
    reporte_md += f"**Fecha de Generación:** {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
    reporte_md += "## 📊 1. Resumen de Datos y Activos\n\n"
    reporte_md += f"* **Activos:** `{', '.join(tickers)}`\n"
    reporte_md += f"* **Período:** `{prices_df.index.min().strftime('%Y-%m-%d')}` a `{prices_df.index.max().strftime('%Y-%m-%d')}`\n"
    
    metricas_activos = pd.DataFrame({
        "Retorno Anualizado": expected_returns,
        "Volatilidad Anualizada": daily_returns.std() * np.sqrt(252)
    })
    reporte_md += "\n### 1.1. Métricas Históricas por Activo\n\n" + metricas_activos.to_markdown(floatfmt=".2%") + "\n\n"

    reporte_md += "## ⚖️ 2. Análisis Comparativo de Portafolios\n\n"
    pesos_df = pd.DataFrame({
        "Cliente": user_portfolio_weights, "Mínimo Riesgo (GMV)": gmv_weights,
        "Máximo Sharpe (MSR)": msr_weights, "Igual Ponderación (EW)": ew_weights
    })
    reporte_md += "### 2.1. Composición de Pesos\n\n" + pesos_df.to_markdown(floatfmt=".2%") + "\n\n"
    
    metricas_portafolios_df = pd.DataFrame({
        "Retorno Anualizado": [user_portfolio_return, gmv_portfolio_return, msr_portfolio_return, ew_portfolio_return],
        "Volatilidad Anualizada": [user_portfolio_volatility, gmv_portfolio_volatility, msr_portfolio_volatility, ew_portfolio_volatility]
    }, index=["Cliente", "GMV", "MSR", "EW"])
    metricas_portafolios_df["Ratio de Sharpe"] = (metricas_portafolios_df["Retorno Anualizado"] - risk_free_rate) / metricas_portafolios_df["Volatilidad Anualizada"]
    reporte_md += "### 2.2. Métricas de Rendimiento y Riesgo\n\n" + metricas_portafolios_df.to_markdown(floatfmt=(".2%", ".2%", ".2f")) + "\n\n"

    reporte_md += "## 🎲 3. Simulación de Monte Carlo\n\n"
    sim_params = simulation_results
    reporte_md += f"* **Escenarios:** `{sim_params['n_scenarios']:,}`\n"
    reporte_md += f"* **Riqueza Terminal Media:** `${sim_params['mean_terminal_wealth']:,.2f}`\n"
    reporte_md += f"* **Riqueza Terminal Mediana:** `${sim_params['median_terminal_wealth']:,.2f}`\n"
    reporte_md += f"* **Rango (5%-95%):** `${sim_params['percentile_5']:,.2f}` - `${sim_params['percentile_95']:,.2f}`\n"

    nombre_archivo = os.path.join(SCRIPT_DIR, "reporte_financiero_exhaustivo.md")
    try:
        with open(nombre_archivo, "w", encoding="utf-8") as f:
            f.write(reporte_md)
        print(f"✅ ¡Éxito! El informe se ha guardado como '{nombre_archivo}'")
    except Exception as e:
        print(f"❌ Error al guardar el informe: {e}")
    
    print("\n--- Vista Previa del Informe ---")
    print(reporte_md)

print("--- 7. Generación de Reportes ---")
generar_informe_financiero_completo()


def capture_portfolio_analysis():
    """Captura todos los resultados del análisis de portafolio."""
    namespace = globals()
    portfolio_results = {'timestamp': datetime.now().isoformat(), 'portfolios': {}, 'monte_carlo': {}, 'visualizations': {}}
    
    try:
        portfolio_results['portfolios']['gmv'] = { 'weights': [float(w) for w in namespace['gmv_weights']], 'return': float(namespace['gmv_portfolio_return']), 'volatility': float(namespace['gmv_portfolio_volatility']) }
        portfolio_results['portfolios']['ew'] = { 'weights': [float(w) for w in namespace['ew_weights']], 'return': float(namespace['ew_portfolio_return']), 'volatility': float(namespace['ew_portfolio_volatility']) }
        portfolio_results['portfolios']['msr'] = { 'weights': [float(w) for w in namespace['msr_weights']], 'return': float(namespace['msr_portfolio_return']), 'volatility': float(namespace['msr_portfolio_volatility']) }
        portfolio_results['portfolios']['user'] = { 'weights': [float(w) for w in namespace['user_portfolio_weights']], 'return': float(namespace['user_portfolio_return']), 'volatility': float(namespace['user_portfolio_volatility']) }
        
        sim_res = namespace['simulation_results']
        portfolio_results['monte_carlo'] = {'scenarios': sim_res['n_scenarios'], 'mean_wealth': float(sim_res['mean_terminal_wealth']), 'median_wealth': float(sim_res['median_terminal_wealth'])}
        
        potential_files = ['portfolio_growth_interactive.html', 'efficient_frontier_interactive.html', 'monte_carlo_trajectories.html', 'msr_portfolio_treemap.html']
        portfolio_results['visualizations']['generated_files'] = [f for f in potential_files if os.path.exists(f)]
        return portfolio_results
    except Exception as e:
        print(f"❌ Error capturando datos para JSON: {e}")
        return portfolio_results

print("\n--- Exportando resultados a JSON ---")
results_json = capture_portfolio_analysis()
output_filename = os.path.join(SCRIPT_DIR, 'portfolio_analysis_results.json')
with open(output_filename, 'w', encoding='utf-8') as f:
    json.dump(results_json, f, indent=2, ensure_ascii=False)
print(f"✅ Resultados guardados en: '{output_filename}'")
print("\n--- Script finalizado ---")