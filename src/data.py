"""Load and clean raw TabFormer transactions, and split them by time (never randomly)."""
import pandas as pd

def load_raw(path, start=0, nrows=3_000_000):
    """Read `nrows` rows of the TabFormer CSV starting after row `start`, keeping the header."""
    
    df=pd.read_csv(path,skiprows=range(1,start+1),nrows=nrows)
    return df

def clean(df):
    """Rename columns, turn amount into a number, is_fraud into 0/1, and build `timestamp`."""
    df.columns=df.columns.str.lower().str.replace(" ","_").str.replace("?","")
    df.amount=df.amount.str.replace("$","").astype(float)
    df["is_fraud"]=(df["is_fraud"]=="Yes").astype(int)
    df["timestamp"] = df["year"].astype(str) + "-" + df["month"].astype(str) + "-" + df["day"].astype(str) + " " + df["time"]
    df["timestamp"] = pd.to_datetime(df["timestamp"], format="%Y-%m-%d %H:%M")
    return df


def time_split(df, cutoff):
    """Return (before, after): rows with timestamp < cutoff, and rows with timestamp >= cutoff."""
    
    before=df[df["timestamp"]<cutoff]
    after=df[df["timestamp"]>=cutoff]
    return before,after
