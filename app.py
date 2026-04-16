import streamlit as st
import pandas as pd
from db import get_connection
from datetime import date


# ---------------- LOGIN FUNCTION ----------------
def login(username, password):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        "SELECT * FROM users WHERE username=%s AND password=%s",
        (username, password)
    )
    user = cursor.fetchone()
    conn.close()
    return user


st.title("Sales Management System")

if "user" not in st.session_state:
    st.session_state.user = None


# ---------------- LOGIN PAGE ----------------
if st.session_state.user is None:

    st.subheader("Login")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        user = login(username, password)
        if user:
            st.session_state.user = user
            st.success("Login Successful")
            st.rerun()
        else:
            st.error("Invalid Credentials")


# ---------------- MAIN APP ----------------
else:

    user = st.session_state.user
    role = user["role"]
    branch_id = user["branch_id"]

    st.write(f"Welcome {user['username']} ({role})")

    if st.button("Logout"):
        st.session_state.user = None
        st.rerun()

    conn = get_connection()

    # ---------------- FILTERS ----------------
    st.subheader("Filters")

    branch_df = pd.read_sql("SELECT * FROM branches", conn)

    if role == "Super Admin":
        branch_option = st.selectbox(
            "Select Branch",
            ["All"] + branch_df["branch_name"].tolist()
        )
    else:
        branch_option = branch_df.loc[
            branch_df["branch_id"] == branch_id, "branch_name"
        ].values[0]

    col1, col2 = st.columns(2)
    from_date = col1.date_input("From Date", value=date(2024, 1, 1))
    to_date = col2.date_input("To Date", value=date.today())

    product_df = pd.read_sql(
        "SELECT DISTINCT product_name FROM customer_sales", conn
    )

    product_option = st.selectbox(
        "Select Product",
        ["All"] + product_df["product_name"].tolist()
    )

    # ---------------- MAIN QUERY ----------------
    query = """
    SELECT 
        cs.sale_id,
        b.branch_name,
        cs.date,
        cs.name,
        cs.mobile_number,
        cs.product_name,
        cs.gross_sales,
        cs.received_amount,
        cs.pending_amount,
        cs.status
    FROM customer_sales cs
    JOIN branches b ON cs.branch_id = b.branch_id
    WHERE 1=1
    """

    params = []

    if role != "Super Admin":
        query += " AND cs.branch_id = %s"
        params.append(int(branch_id))

    elif branch_option != "All":
        branch_id_selected = int(branch_df.loc[
            branch_df["branch_name"] == branch_option, "branch_id"
        ].values[0])

        query += " AND cs.branch_id = %s"
        params.append(branch_id_selected)

    query += " AND cs.date BETWEEN %s AND %s"
    params.extend([from_date, to_date])

    if product_option != "All":
        query += " AND cs.product_name = %s"
        params.append(product_option)

    df = pd.read_sql(query, conn, params=params)

    # ---------------- KPI ----------------
    st.subheader("Dashboard KPIs")

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Sales", df["gross_sales"].sum())
    col2.metric("Total Received", df["received_amount"].sum())
    col3.metric("Total Pending", df["pending_amount"].sum())

    # ---------------- TABLE ----------------
    st.subheader("Filtered Sales Data")
    st.dataframe(df)

    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button("Download CSV", csv, "sales_data.csv")

    # =====================================================
    # CUSTOMER FORM
    # =====================================================
    st.subheader("Add Customer")

    branch_map = dict(zip(branch_df["branch_name"], branch_df["branch_id"]))

    with st.form("customer_form"):
        branch_name = st.selectbox("Branch", list(branch_map.keys()))
        sale_date = st.date_input("Date")
        cust_name = st.text_input("Customer Name")
        mobile = st.text_input("Mobile Number")
        product = st.selectbox("Product", ["DS", "FSD", "DA", "BA"])
        gross = st.number_input("Total Amount", min_value=0)

        submit_customer = st.form_submit_button("Add Customer")

        if submit_customer:
            cursor = conn.cursor()

            cursor.execute("SELECT IFNULL(MAX(sale_id),0)+1 FROM customer_sales")
            new_id = cursor.fetchone()[0]

            cursor.execute("""
                INSERT INTO customer_sales 
                (sale_id, branch_id, date, name, mobile_number, product_name, gross_sales)
                VALUES (%s,%s,%s,%s,%s,%s,%s)
            """, (
                new_id,
                branch_map[branch_name],
                sale_date,
                cust_name,
                mobile,
                product,
                gross
            ))

            conn.commit()
            st.success("Customer Added Successfully")
            st.rerun()

    # =====================================================
    # PAYMENT FORM
    # =====================================================
    st.subheader("Add Payment")

    with st.form("payment_form"):
        sale_id = st.number_input("Sale ID", min_value=1)
        amount = st.number_input("Amount", min_value=0)
        method = st.selectbox("Method", ["Cash", "UPI", "Card"])

        submit_payment = st.form_submit_button("Add Payment")

        if submit_payment:
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO payment_splits 
                (sale_id, payment_date, amount_paid, payment_method)
                VALUES (%s, CURDATE(), %s, %s)
            """, (sale_id, amount, method))

            conn.commit()
            st.success("Payment Added Successfully")
            st.rerun()

    # =====================================================
    # PAYMENT SUMMARY
    # =====================================================
    st.subheader("Payment Method Summary")

    payment_query = """
    SELECT ps.payment_method, SUM(ps.amount_paid) as total
    FROM payment_splits ps
    JOIN customer_sales cs ON ps.sale_id = cs.sale_id
    WHERE 1=1
    """

    payment_params = []

    if role != "Super Admin":
        payment_query += " AND cs.branch_id = %s"
        payment_params.append(int(branch_id))

    elif branch_option != "All":
        payment_query += " AND cs.branch_id = %s"
        payment_params.append(branch_id_selected)

    payment_query += " AND cs.date BETWEEN %s AND %s"
    payment_params.extend([from_date, to_date])

    if product_option != "All":
        payment_query += " AND cs.product_name = %s"
        payment_params.append(product_option)

    payment_query += " GROUP BY ps.payment_method"

    payment_df = pd.read_sql(payment_query, conn, params=payment_params)

    st.dataframe(payment_df)

    if not payment_df.empty:
        st.bar_chart(payment_df.set_index("payment_method"))

    # =====================================================
    # 🚀 SQL ANALYSIS / REPORTS (NEW REQUIREMENT)
    # =====================================================
    st.subheader("SQL Analysis / Reports")

    report = st.selectbox("Choose Report", [
        "Total Sales by Branch",
        "Total Sales by Product",
        "Monthly Sales Trend",
        "Top Customers",
        "Pending vs Received",
        "Daily Sales Report",
        "Branch Performance"
    ])

    if report == "Total Sales by Branch":
        q = """
        SELECT b.branch_name, SUM(cs.gross_sales) total_sales
        FROM customer_sales cs
        JOIN branches b ON cs.branch_id = b.branch_id
        GROUP BY b.branch_name
        """
        st.dataframe(pd.read_sql(q, conn))

    elif report == "Total Sales by Product":
        q = """
        SELECT product_name, SUM(gross_sales) total_sales
        FROM customer_sales
        GROUP BY product_name
        """
        st.dataframe(pd.read_sql(q, conn))

    elif report == "Monthly Sales Trend":
        q = """
        SELECT DATE_FORMAT(date,'%Y-%m') month, SUM(gross_sales) total_sales
        FROM customer_sales
        GROUP BY month
        ORDER BY month
        """
        st.line_chart(pd.read_sql(q, conn).set_index("month"))

    elif report == "Top Customers":
        q = """
        SELECT name, SUM(gross_sales) total_spent
        FROM customer_sales
        GROUP BY name
        ORDER BY total_spent DESC
        LIMIT 10
        """
        st.dataframe(pd.read_sql(q, conn))

    elif report == "Pending vs Received":
        q = """
        SELECT SUM(gross_sales) sales,
               SUM(received_amount) received,
               SUM(pending_amount) pending
        FROM customer_sales
        """
        st.dataframe(pd.read_sql(q, conn))

    elif report == "Daily Sales Report":
        q = """
        SELECT date, SUM(gross_sales) total_sales
        FROM customer_sales
        GROUP BY date
        ORDER BY date
        """
        st.line_chart(pd.read_sql(q, conn).set_index("date"))

    elif report == "Branch Performance":
        q = """
        SELECT b.branch_name,
               SUM(cs.gross_sales) sales,
               SUM(cs.received_amount) received
        FROM customer_sales cs
        JOIN branches b ON cs.branch_id = b.branch_id
        GROUP BY b.branch_name
        """
        st.dataframe(pd.read_sql(q, conn))

    conn.close()