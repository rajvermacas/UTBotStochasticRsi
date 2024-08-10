import numpy as np


def calculate_skewness(data):
    """
    Calculate the skewness of the given data and plot its distribution.

    Parameters
    ----------
    data : array-like
        The data for which the skewness is to be calculated.

    Returns
    -------
    float
        The skewness of the data.
    """
    if not data:
        return np.nan
    # Convert data to a numpy array if it's not already
    data = np.array(data)

    # Calculate the mean of the data
    mean_data = np.mean(data)

    # Calculate the standard deviation of the data
    std_dev_data = np.std(data)
    if std_dev_data == 0:
        return np.nan

    # Calculate the skewness using the formula for skewness
    skewness = np.sum((data - mean_data) ** 3) / (len(data) * (std_dev_data ** 3))
    skewness = round(skewness, 2)

    return skewness

def calculate_sharpe_ratio(returns, risk_free_rate=0.05):
    """
    Calculate the Sharpe Ratio for the given returns.

    Parameters
    ----------
    returns : array-like
        The returns for which the Sharpe Ratio is to be calculated.
    risk_free_rate : float, optional
        The risk-free rate of return, by default 0.0

    Returns
    -------
    float
        The Sharpe Ratio.
    """
    if not returns:
        return np.nan
    # Convert returns to a numpy array if it's not already
    returns = np.array(returns)

    # Calculate the excess returns by subtracting the risk-free rate
    excess_returns = returns - risk_free_rate

    # Calculate the mean of excess returns
    mean_excess_returns = np.mean(excess_returns)

    # Calculate the standard deviation of returns
    std_dev_returns = np.std(returns)

    # Calculate the Sharpe Ratio
    if std_dev_returns == 0:
        return np.nan  # Return NaN if standard deviation is zero to avoid division by zero

    return round(mean_excess_returns / std_dev_returns, 2)

def calculate_max_drawdown(transactions):
    """
    Calculate the maximum drawdown from a list of transactions.
    
    Parameters:
    transactions (list): A list of Transaction objects.
    
    Returns:
    float: The maximum drawdown as a percentage.
    """
    peak = -float('inf')
    max_drawdown = 0
    
    for transaction in transactions:
        peak = max(peak, transaction.sell_price)
        drawdown = (peak - transaction.sell_price) / peak * 100
        max_drawdown = max(max_drawdown, drawdown)
    
    return max_drawdown