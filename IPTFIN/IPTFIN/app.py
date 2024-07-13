from flask import Flask, request, render_template, redirect, url_for
import pandas as pd
import os
import plotly.express as px
import plotly.graph_objects as go
from sqlalchemy import create_engine
from scipy import stats
import plotly.io as pio
import numpy as np

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'

# MySQL connection setup
DATABASE_URI = 'mysql+pymysql://root:12345@localhost:3306/sample'
engine = create_engine(DATABASE_URI)


dataframe_html = None
creative_types_dataframe_html = None
annual_ticket_sales_dataframe_html = None
summary_data = None
dataframe_html = None
highest_grossers_chart_html = None
creative_types_chart_html = None
annual_ticket_sales_chart_html = None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    global highest_grossers_df, popular_creative_types_df, annual_ticket_sales_df
    
    if 'files' not in request.files:
        return redirect(request.url)

    files = request.files.getlist('files')
    if not files or files[0].filename == '':
        return redirect(request.url)

    highest_grossers_df = None
    popular_creative_types_df = None
    annual_ticket_sales_df = None

    for file in files:
        if file:
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.save(filepath)

            if file.filename == 'HighestGrossers.csv':
                highest_grossers_df = pd.read_csv(filepath)
                highest_grossers_df["GENRE"].fillna("Adventure", inplace=True)
                highest_grossers_df.at[25, 'GENRE'] = "Action"
                highest_grossers_df["TICKETS SOLD"] = highest_grossers_df["TICKETS SOLD"].str.replace(",", "")

                for col in ["TOTAL FOR YEAR", "TOTAL IN 2019 DOLLARS"]:
                    highest_grossers_df[col] = highest_grossers_df[col].str.replace(",", "")
                    highest_grossers_df[col] = highest_grossers_df[col].str.replace("$", "")

                for col in ["TICKETS SOLD", "TOTAL FOR YEAR", "TOTAL IN 2019 DOLLARS"]:
                    highest_grossers_df[col] = pd.to_numeric(highest_grossers_df[col], errors='coerce')

            elif file.filename == 'PopularCreativeTypes.csv':
                popular_creative_types_df = pd.read_csv(filepath)
                popular_creative_types_df["MOVIES"] = popular_creative_types_df["MOVIES"].str.replace(",", "")
                
                for col in ["TOTAL GROSS", "AVERAGE GROSS"]:
                    popular_creative_types_df[col] = popular_creative_types_df[col].str.replace(",", "")
                    popular_creative_types_df[col] = popular_creative_types_df[col].str.replace("$", "")
                
                for col in ["TOTAL GROSS", "AVERAGE GROSS", "MOVIES"]:
                    popular_creative_types_df[col] = pd.to_numeric(popular_creative_types_df[col], errors='coerce')
                
                # Remove rows where all values are NaN
                popular_creative_types_df = popular_creative_types_df.dropna(how='all')

            elif file.filename == 'AnnualTicketSales.csv':
                annual_ticket_sales_df = pd.read_csv(filepath)
                annual_ticket_sales_df["TICKETS SOLD"] = annual_ticket_sales_df["TICKETS SOLD"].str.replace(",", "")
                
                for col in ["TOTAL BOX OFFICE", "TOTAL INFLATION ADJUSTED BOX OFFICE", "AVERAGE TICKET PRICE"]:
                    annual_ticket_sales_df[col] = annual_ticket_sales_df[col].str.replace(",", "")
                    annual_ticket_sales_df[col] = annual_ticket_sales_df[col].str.replace("$", "")
                
                annual_ticket_sales_df = annual_ticket_sales_df.drop(labels="Unnamed: 5", axis=1)
                for col in ["TICKETS SOLD", "TOTAL BOX OFFICE"]:
                    annual_ticket_sales_df[col] = pd.to_numeric(annual_ticket_sales_df[col], errors='coerce')

                # Calculation for plot
                x = list(range(0, (2020-1995)))
                y = list(annual_ticket_sales_df['TOTAL BOX OFFICE'])
                y.reverse()
                y.pop()
                y.pop()
                slope, intercept, r, p, std_err = stats.linregress(x, y)
                x1 = list(range(0, (2022-1995)))
                y1 = [slope * x + intercept for x in x1]
                y1.reverse()
                annual_ticket_sales_df['TOTAL BOX OFFICE WITHOUT COVID'] = y1
                annual_ticket_sales_df["Diff"] = annual_ticket_sales_df['TOTAL BOX OFFICE WITHOUT COVID'] - annual_ticket_sales_df['TOTAL BOX OFFICE']

    if highest_grossers_df is not None:
        global summary_data, dataframe_html
        summary_data = highest_grossers_df.describe().to_html()
        dataframe_html = highest_grossers_df.to_html(float_format='{:,.0f}'.format)  # Display all rows with float format

        try:
            highest_grossers_df.describe().to_sql('summary', engine, if_exists='replace', index=False)
        except Exception as e:
            return f"An error occurred while saving to the database: {e}"

    if popular_creative_types_df is not None:
        global creative_types_dataframe_html
        creative_types_dataframe_html = popular_creative_types_df.to_html(float_format='{:,.0f}'.format)  # Display all rows with float format

    if highest_grossers_df is not None:
        highest_grossers_chart_html = generate_highest_grossers_plot(highest_grossers_df)
        distributor_genre_chart_html = generate_highest_grossers_by_distributor_genre_plot(highest_grossers_df)
        distributor_rating_chart_html = generate_highest_grossers_by_distributor_rating_plot(highest_grossers_df)

    if annual_ticket_sales_df is not None:
        global annual_ticket_sales_dataframe_html
        # Create a copy without the 'TOTAL BOX OFFICE WITHOUT COVID' column for rendering
        annual_ticket_sales_df_for_html = annual_ticket_sales_df.drop(columns=['TOTAL BOX OFFICE WITHOUT COVID', 'Diff'])
        annual_ticket_sales_dataframe_html = annual_ticket_sales_df_for_html.to_html(float_format='{:,.0f}'.format)  # Display all rows with float format

    return redirect(url_for('summary'))






@app.route('/summary')
def summary():
    global summary_data, dataframe_html, highest_grossers_chart_html, creative_types_chart_html, annual_ticket_sales_chart_html

    # Generating charts if dataframes are not None
    if dataframe_html is not None:
        highest_grossers_chart_html = generate_highest_grossers_plot(highest_grossers_df)
        distributor_genre_chart_html = generate_highest_grossers_by_distributor_genre_plot(highest_grossers_df)
        distributor_rating_chart_html = generate_highest_grossers_by_distributor_rating_plot(highest_grossers_df)
    
    if creative_types_dataframe_html is not None:
        creative_types_chart_html = generate_creative_types_plot(popular_creative_types_df)

    if annual_ticket_sales_dataframe_html is not None:
        annual_ticket_sales_chart_html = generate_annual_ticket_sales_plot(annual_ticket_sales_df)
    
    return render_template('summary.html', 
                       summary_data=summary_data, 
                       dataframe_html=dataframe_html, 
                       highest_grossers_chart_html=highest_grossers_chart_html, 
                       creative_types_chart_html=creative_types_chart_html, 
                       highest_grossers_by_distributor_genre_chart_html=distributor_genre_chart_html,
                       highest_grossers_by_distributor_rating_chart_html=distributor_rating_chart_html,
                       creative_types_dataframe_html=creative_types_dataframe_html,
                       annual_ticket_sales_chart_html=annual_ticket_sales_chart_html,
                       annual_ticket_sales_dataframe_html=annual_ticket_sales_dataframe_html)




@app.route('/dataframe/<string:csv_name>')
def show_dataframe(csv_name):
    if csv_name == 'HighestGrossers':
        return render_template('dataframe.html', dataframe_html=dataframe_html)
    elif csv_name == 'PopularCreativeTypes':
        return render_template('dataframe.html', dataframe_html=creative_types_dataframe_html)
    elif csv_name == 'AnnualTicketSales':
        return render_template('dataframe.html', dataframe_html=annual_ticket_sales_dataframe_html)
    else:
        return "Invalid CSV name."
    
def load_dataframe(filename):
    try:
        print(f"Attempting to load file: static/{filename}")  # Debug print
        df = pd.read_csv(f'static/{filename}')
        print(f"File loaded successfully: static/{filename}")  # Debug print
        return df
    except FileNotFoundError:
        print(f"File not found: static/{filename}")  # Debug print
        return None
    except Exception as e:
        print(f"Error loading file {filename}: {e}")  # Debug print
        return None


def foo(x):
    if len(str(x)) == 7:
        return "Tickets Sold: " + str(x)[0:1] + " Million"
    elif len(str(x)) == 8:
        return "Tickets Sold: " + str(x)[0:2] + " Million"
    elif len(str(x)) == 9:
        return "Tickets Sold: " + str(x)[0:3] + " Million"
    elif len(str(x)) == 10:
        return "Tickets Sold: " + str(x)[0:1] + "." + str(x)[1:2] + " Billion"
    elif len(str(x)) == 11:
        return "Tickets Sold: " + str(x)[0:2] + "." + str(x)[2:3] + " Billion"
    else:
        return "Tickets Sold: " + str(x)[0:3] + "." + str(x)[3:4] + " Billion"

def foo_2(x):
    if len(str(x)) == 7:
        return "Total Box Office: " + str(x)[0:1] + " Million"
    elif len(str(x)) == 8:
        return "Total Box Office: " + str(x)[0:2] + " Million"
    elif len(str(x)) == 9:
        return "Total Box Office: " + str(x)[0:3] + " Million"
    elif len(str(x)) == 10:
        return "Total Box Office: " + str(x)[0:1] + "." + str(x)[1:2] + " Billion"
    elif len(str(x)) == 11:
        return "Total Box Office: " + str(x)[0:2] + "." + str(x)[2:3] + " Billion"
    else:
        return "Total Box Office: " + str(x)[0:3] + "." + str(x)[3:4] + " Billion"

def foo_3(x):
    if len(str(x)) <= 9:
        return "$" + str(x)[0:3] + " M"
    else:
        return "$" + str(x)[0:1] + "." + str(x)[1:2] + " B"

def foo_4(x):
    if len(str(x)) <= 9:
        return "$" + str(x)[0:3] + " M Total Gross"
    elif len(str(x)) == 10:
        return "$" + str(x)[0:1] + "." + str(x)[1:2] + " B Total Gross"
    elif len(str(x)) == 11:
        return "$" + str(x)[0:2] + "." + str(x)[2:3] + " B Total Gross"
    else:
        return "$" + str(x)[0:3] + "." + str(x)[3:4] + " B Total Gross"

def foo_5(x):
    if len(str(x)) == 7:
        return "$" + str(x)[0:1] + "." + str(x)[1:2] + " M Average Gross"
    elif len(str(x)) == 8:
        return "$" + str(x)[0:2] + "." + str(x)[2:3] + " M Average Gross"
    elif len(str(x)) == 9:
        return "$" + str(x)[0:3] + "." + str(x)[3:4] + " M Average Gross"
    elif len(str(x)) == 10:
        return "$" + str(x)[0:1] + "." + str(x)[1:2] + " B Average Gross"
    elif len(str(x)) == 11:
        return "$" + str(x)[0:2] + "." + str(x)[2:3] + " B Average Gross"
    else:
        return "$" + str(x)[0:3] + "." + str(x)[3:4] + " B Average Gross"

def generate_highest_grossers_plot(highest_grossers_df):
    fig = go.Figure()

    highest_grossers_df["tickets_sold"] = highest_grossers_df["TICKETS SOLD"] * 3
    highest_grossers_df["TS"] = highest_grossers_df["TICKETS SOLD"].apply(foo)
    highest_grossers_df["TBO"] = highest_grossers_df["TOTAL FOR YEAR"].apply(foo_2)

    highest_grossers_df["TOTAL FOR YEAR"] = highest_grossers_df["TOTAL FOR YEAR"].fillna(0)
    highest_grossers_df["tickets_sold"] = highest_grossers_df["tickets_sold"].fillna(0)

    fig1 = px.line(highest_grossers_df, x="YEAR", y="TOTAL FOR YEAR", custom_data=["MOVIE"], color_discrete_sequence=["black"])
    fig1.update_traces(hovertemplate="<br>".join(["<b>%{customdata[0]}<b>"]))

    fig2 = px.scatter(highest_grossers_df, x="YEAR", y="TOTAL FOR YEAR", color="DISTRIBUTOR", custom_data=["DISTRIBUTOR", "TBO"], size="TOTAL FOR YEAR", opacity=0.8)
    fig2.update_traces(hovertemplate="<br>".join(["<b>%{customdata[0]}<b>", "<b>%{customdata[1]}<b>"]))

    fig3 = px.bar(highest_grossers_df, x="YEAR", y="tickets_sold", custom_data=["MOVIE", "TS"], color="GENRE", opacity=0.7, title="Highest Grossing Movies Each Year")
    fig3.update_traces(hovertemplate="<br>".join(["<b>%{customdata[0]}<b>", "<b>%{customdata[1]}<b>"]))

    fig.add_traces(fig1.data + fig2.data + fig3.data)
    fig.update_layout(hovermode="x unified", template="simple_white")
    fig.update_layout(title_x=0.5, font_family="Rockwell", legend=dict(title=None, orientation="h", y=1, yanchor="bottom", x=0.5, xanchor="center"))
    fig.update_yaxes(visible=False, showticklabels=False)

    return fig.to_html(full_html=False)

def generate_creative_types_plot(popular_creative_types_df):
    fig = go.Figure()

    popular_creative_types_df = popular_creative_types_df.sort_values("MOVIES", ascending=False).reset_index()
    popular_creative_types_df["total_gross"] = popular_creative_types_df["TOTAL GROSS"] / 10000000
    popular_creative_types_df["avg_gross"] = popular_creative_types_df["AVERAGE GROSS"] / 19000

    popular_creative_types_df["TG"] = popular_creative_types_df["TOTAL GROSS"].apply(foo_4)
    popular_creative_types_df["TG2"] = popular_creative_types_df["TOTAL GROSS"].apply(foo_4)
    popular_creative_types_df["M"] = popular_creative_types_df["MOVIES"].apply(lambda x: str(x) + " Movies")
    popular_creative_types_df["AVG"] = popular_creative_types_df["AVERAGE GROSS"].apply(foo_5)

    popular_creative_types_df["AVERAGE GROSS"] = popular_creative_types_df["AVERAGE GROSS"].fillna(0)

    fig4 = px.bar(popular_creative_types_df, x="CREATIVE TYPES", y="MOVIES", custom_data=["M"], color_discrete_sequence=["burlywood"])
    fig4.update_traces(hovertemplate="<br>".join(["<b>%{customdata[0]}<b>"]))

    fig5 = px.bar(popular_creative_types_df, x="CREATIVE TYPES", y="total_gross", custom_data=["TG"], color_discrete_sequence=["lightseagreen"])
    fig5.update_traces(hovertemplate="<br>".join(["<b>%{customdata[0]}<b>"]))

    fig6 = px.scatter(popular_creative_types_df, x="CREATIVE TYPES", y="avg_gross", custom_data=["AVG"], size="AVERAGE GROSS", size_max=50, opacity=0.9, color_discrete_sequence=["DarkSlateGray"])
    fig6.update_traces(hovertemplate="<br>".join(["<b>%{customdata[0]}<b>"]))

    fig.add_traces(fig4.data + fig5.data + fig6.data)
    fig.update_layout(hovermode="x unified", template="simple_white", title="Creative Types Overview")
    fig.update_layout(title_x=0.5, font_family="Rockwell", legend=dict(title=None, orientation="h", y=1, yanchor="bottom", x=0.5, xanchor="center"))
    fig.update_yaxes(visible=False, showticklabels=False)

    return fig.to_html(full_html=False)


def generate_highest_grossers_by_distributor_genre_plot(highest_grossers_df):
    # Ensure columns are strings before replacing characters
    highest_grossers_df["TOTAL IN 2019 DOLLARS"] = highest_grossers_df["TOTAL IN 2019 DOLLARS"].astype(str).str.replace(',', '').str.replace('$', '')
    highest_grossers_df["TICKETS SOLD"] = highest_grossers_df["TICKETS SOLD"].astype(str).str.replace(',', '')

    # Convert columns to float after cleaning
    highest_grossers_df['TOTAL IN 2019 DOLLARS'] = highest_grossers_df['TOTAL IN 2019 DOLLARS'].astype(float)
    highest_grossers_df['TICKETS SOLD'] = highest_grossers_df['TICKETS SOLD'].astype(float)

    # Group by 'DISTRIBUTOR' and 'GENRE'
    df_g = highest_grossers_df.groupby(by=['DISTRIBUTOR', 'GENRE'])['TICKETS SOLD'].sum().unstack()

    # Plotting the new chart
    fig = px.bar(df_g, barmode='group')
    fig.update_layout(title='Tickets Sold by Distributor and Genre', xaxis_title='Distributor', yaxis_title='Tickets Sold')
    
    return fig.to_html(full_html=False)

def generate_highest_grossers_by_distributor_rating_plot(highest_grossers_df):
    # Ensure columns are strings before replacing characters
    highest_grossers_df["TOTAL IN 2019 DOLLARS"] = highest_grossers_df["TOTAL IN 2019 DOLLARS"].astype(str).str.replace(',', '').str.replace('$', '')
    highest_grossers_df["TICKETS SOLD"] = highest_grossers_df["TICKETS SOLD"].astype(str).str.replace(',', '')

    # Convert columns to float after cleaning
    highest_grossers_df['TOTAL IN 2019 DOLLARS'] = highest_grossers_df['TOTAL IN 2019 DOLLARS'].astype(float)
    highest_grossers_df['TICKETS SOLD'] = highest_grossers_df['TICKETS SOLD'].astype(float)

    # Group by 'DISTRIBUTOR' and 'MPAA RATING'
    df_g = highest_grossers_df.groupby(by=['DISTRIBUTOR', 'MPAA RATING'])['TICKETS SOLD'].sum().unstack()

    # Plotting the new chart
    fig = px.bar(df_g, barmode='group')
    fig.update_layout(title='Tickets Sold by Distributor and MPAA Rating', xaxis_title='Distributor', yaxis_title='Tickets Sold')
    
    return fig.to_html(full_html=False)

# New plot function for AnnualTicketSales.csv

def generate_annual_ticket_sales_plot(df):
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=df['YEAR'],
        y=df['TOTAL BOX OFFICE'],
        mode='lines+markers',
        name='Total Box Office',
        line=dict(color='blue'),
        text=df['TICKETS SOLD'].apply(lambda x: f'Tickets Sold: {x:,.0f}'),
        hovertemplate='%{x}<br>Total Box Office: $%{y:,.2f}<br>%{text}'
    ))

    fig.add_trace(go.Scatter(
        x=df['YEAR'],
        y=df['TOTAL BOX OFFICE WITHOUT COVID'],
        mode='lines',
        name='Total Box Office (without COVID)',
        line=dict(color='red', dash='dash'),
        hovertemplate='%{x}<br>Total Box Office (without COVID): $%{y:,.2f}'
    ))

    fig.update_layout(
        title="Annual Ticket Sales",
        xaxis_title="Year",
        yaxis_title="Total Box Office",
        showlegend=True
    )

    return fig.to_html(full_html=False)

if __name__ == '__main__':
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
    if not os.path.exists('static'):
        os.makedirs('static')
    app.run(debug=True)