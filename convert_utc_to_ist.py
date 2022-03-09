from dateutil import parser
import datetime


def convert_utc_ist(utc):
    # utc = '2022-03-08T07:00:21.971538Z'  # or any date string of differing formats.
    utc_time = parser.parse(utc)
    # print(utc_time)
    hours = 5.30
    hours_added = datetime.timedelta(hours=hours)
    ist_time = utc_time + hours_added
    # print(ist_time)
    return ist_time


def main():
    utc_test_time = "2022-03-08T07:00:21.971538Z"
    ist = convert_utc_ist(utc=utc_test_time)
    print(f"The UTC time is {utc_test_time}")
    print(f"The IST time is - {ist}")


if __name__ == "__main__":
    main()
