from flask import Flask, render_template, request, redirect, url_for, send_from_directory, flash
import os
import sqlite3

from datetime import datetime
from config import Config

app = Flask(__name__)
app.config.from_object(Config)
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize database
def init_db():
    with sqlite3.connect('database.db') as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS applicants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            email TEXT,
            phone TEXT,
            notes TEXT,
            resume_filename TEXT,
            status TEXT DEFAULT 'Submitted',
            submitted_at TEXT
        )''')
init_db()

@app.route('/')
def index():
    return render_template('form.html')

@app.route('/submit', methods=['POST'])
def submit():
    name = request.form['name']
    email = request.form['email']
    phone = request.form['phone']

    # Phone validation: only digits allowed
    if phone and not phone.isdigit():
        flash('Phone number must contain digits only.')
        return redirect(url_for('index'))

    notes = request.form['notes']
    resume = request.files['resume']

    resume_filename = None
    if resume:
        resume_filename = resume.filename
        resume.save(os.path.join(app.config['UPLOAD_FOLDER'], resume_filename))

    submitted_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    with sqlite3.connect('database.db') as conn:
        conn.execute('''
            INSERT INTO applicants (name, email, phone, notes, resume_filename, submitted_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (name, email, phone, notes, resume_filename, submitted_at))

    flash('Your application has been submitted successfully!')
    return redirect(url_for('index'))

@app.route('/admin')
def admin():
    with sqlite3.connect('database.db') as conn:
        cursor = conn.execute('SELECT id, name, email, phone, notes, resume_filename, status, submitted_at FROM applicants')
        applicants = cursor.fetchall()

        # Count statuses
        total = len(applicants)
        submitted = sum(1 for a in applicants if a[6] == 'Submitted')
        under_review = sum(1 for a in applicants if a[6] == 'Under Review')
        interviewing = sum(1 for a in applicants if a[6] == 'Interviewing')
        accepted = sum(1 for a in applicants if a[6] == 'Accepted')
        rejected = sum(1 for a in applicants if a[6] == 'Rejected')

    # Running counter: track how many times each email has appeared so far
    email_running_count = {}
    email_labels = []

    for a in applicants:
        email = a[2]
        count = email_running_count.get(email, 0) + 1
        email_running_count[email] = count
        label = f"{email} ({count})" if count > 1 else email
        email_labels.append(label)

    return render_template(
        'admin.html',
        applicants=applicants,
        total=total,
        submitted=submitted,
        under_review=under_review,
        interviewing=interviewing,
        accepted=accepted,
        rejected=rejected,
        email_labels=email_labels
    )

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/status', methods=['GET', 'POST'])
def check_status():
    if request.method == 'POST':
        email = request.form['email']
        with sqlite3.connect('database.db') as conn:
            cursor = conn.execute("SELECT name, email, status FROM applicants WHERE email = ?", (email,))
            result = cursor.fetchone()
        return render_template('status_result.html', result=result, email=email)
    return render_template('status_check.html')

@app.route('/update_status', methods=['POST'])
def update_status():
    applicant_id = request.form['applicant_id']
    new_status = request.form['status']

    with sqlite3.connect('database.db') as conn:
        conn.execute("UPDATE applicants SET status = ? WHERE id = ?", (new_status, applicant_id))
    flash('Status updated successfully.')
    return redirect(url_for('admin'))

@app.route('/delete/<int:applicant_id>', methods=['POST'])
def delete_applicant(applicant_id):
    with sqlite3.connect('database.db') as conn:
        # Optionally delete uploaded file too
        cursor = conn.execute("SELECT resume_filename FROM applicants WHERE id = ?", (applicant_id,))
        row = cursor.fetchone()
        if row and row[0]:
            try:
                os.remove(os.path.join(app.config['UPLOAD_FOLDER'], row[0]))
            except FileNotFoundError:
                pass

        # Delete the record
        conn.execute("DELETE FROM applicants WHERE id = ?", (applicant_id,))
    flash('Applicant deleted.')
    return redirect(url_for('admin'))

if __name__ == '__main__':
    app.run(debug=True)


