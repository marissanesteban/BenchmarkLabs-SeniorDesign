from seebuoy import NDBC
import pandas as pd
from datetime import datetime, timedelta
from prophet import Prophet

def buoySetUp(buoyNum):  
    """
    Parameters:
    buoyNum: A string value that represents a buoy in the NDBC system

    Returns: A pandas df that contains the historical data of the selected buoy
    """
    ndbc = NDBC(timeframe="historical")

    valid = False
    while (not valid):
        try:
            df_avail = ndbc.available_data(station_id=buoyNum)
            df_data = ndbc.get_data(buoyNum)
            valid = True
        except ValueError:
            buoyNum = input("Please enter a valid buoy number: ")
        
    df_data.dropna(axis=1, how='all', inplace=True)
    df_data = df_data.reset_index()

    if 'wave_height' not in df_data.columns or 'average_period' not in df_data.columns:
        print("Not enough data")
        return False

    # lets limit the df to 2 columns: date and wave height
    buoy_df = df_data[["date","wave_height", "average_period"]]

    # Set 'date' column as the index
    buoy_df = buoy_df.set_index("date")

    buoy_df['wave_height_interpolated'] = buoy_df['wave_height'].interpolate(method='time') # interpolate missing values based on time
    buoy_df['average_period_interpolated'] = buoy_df['average_period'].interpolate(method='time') # interpolate missing values based on time

    return buoy_df


def make_predictions(buoy_df, targetVariable):
    """
    Parameters:
    buoy_df: The dataframe of the selected buoy that contains the histroical data of the buoy
    targetVariable: Either "wave_height" or "average_period", this decides what variable we predict for

    Return:
    forecast: A dataframe with the forecasted data 15 days in advance
    """
    #Reset the index of the buoy dataframe
    buoy_df = buoy_df.reset_index()

    #Gets todays date
    today_date = datetime.today().date()

    #Gets the date two years ago today
    trainDate = today_date - timedelta(days=730)

    #Subsets the whole dataframe to be just the last two years of data
    training_df = buoy_df[buoy_df['date'] > pd.Timestamp(trainDate)]

    #Sets up the modeling df with the date and target variable column as well as the cap for logistic growth prophet algo
    modeling_df = training_df[["date",f'{targetVariable}_interpolated']]
    modeling_df = modeling_df.rename(columns={"date": "ds", f'{targetVariable}_interpolated': "y"})
    cap = modeling_df['y'].max() + 1

    # Initialize Prophet model with the cap
    model = Prophet(growth="logistic")
    modeling_df['cap'] = cap
    model.fit(modeling_df)

    #Makes prediction
    future = model.make_future_dataframe(periods=15)
    future['cap'] = cap
    forecast = model.predict(future)

    forecast['date'] = forecast['ds']

    return forecast

def to_html(html):

    opening = "<!DOCTYPE html><html><head><title>Predictions</title></head><body><h1>Predictions</h1><p>"
    closing = "</p></body></html>"

    html_output = opening + html + closing

    with open("output_html.html", "w") as file:
        file.write(html_output)

def to_table(future):

    table = []
    
    for index, row in future.iterrows():
        day = datetime.strptime(str(row['ds']), "%Y-%m-%d %H:%M:%S").strftime("%A %B %d")
        high_low = str(round(row['yhat_lower'],2))+" / "+ str(round(row['yhat_upper'],2))
        predicted = str(round(row['yhat'],2))
        
        table.append([day, high_low, predicted])
    
    return table

def main():
    # list of valid buoys (based on research)
    buoy_list = ["44065", "44085", "44013", "46253", "46053"]
    variable_list = ['wave_height', 'average_period']

    # prompting user to enter a port of interest
    location_choice = 0
    while not (1<=location_choice and location_choice <=5):
        print("1 - Booklyn, NY \n2 - New Bedford, MA \n3 - Salem, MA \n4 - Los Angeles, CA \n5 - Santa Barbara, CA")
        location_choice = int(input("Enter a port of interest (1-5): "))

    # prompting user to enter a target variable
    target_variable_choice = 0
    while target_variable_choice != 1 and target_variable_choice != 2:
        print("1 - Wave Height \n2 - Wave Period")
        target_variable_choice = int(input("Enter prediction choice: "))

    # Calls buoySetUp with the selected buoy dataframe
    buoy_df = buoySetUp(buoy_list[location_choice-1])
    target_variable = variable_list[target_variable_choice - 1]

    #Calls make_predictions
    forecast = make_predictions(buoy_df, target_variable)

    #Gets tomorrows date and subsets the forecast dataframe to isolate the predictions
    today = pd.Timestamp.today() + timedelta(days=1)
    future = forecast[forecast['ds'] > today]

    html = "{:<30} {:<30} {:<10}".format("Date", "Wave Height Forecasted (m)", "yhat upper / yhat lower<br /><br /><br />")
    print("{:<30} {:<30} {:<10}".format("Date", "Wave Height Forecasted (m)", "yhat upper / yhat lower"))
    print()
    for index, row in future.iterrows():
        day = datetime.strptime(str(row['ds']), "%Y-%m-%d %H:%M:%S").strftime("%A %B %d")
        high_low = str(round(row['yhat_lower'],2))+" / "+ str(round(row['yhat_upper'],2))
        predicted = str(round(row['yhat'],2))
        print("{:<30} {:<30} {:<10}".format(day, predicted, high_low ))

        html += "{:<30} {:<30} {:<10}<br />".format(day, predicted, high_low)   
    
    to_html(html)

    table = to_table(future)


if __name__ == "__main__":
    main()