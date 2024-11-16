from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///skincare.db'
db = SQLAlchemy(app)

class Entry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    morning_routine = db.Column(db.Text)
    evening_routine = db.Column(db.Text)
    skin_condition = db.Column(db.String(100))
    notes = db.Column(db.Text)

with app.app_context():
    db.create_all()

@app.route('/')
def index():
    entries = Entry.query.order_by(Entry.date.desc()).all()
    return render_template('index.html', entries=entries)

@app.route('/add', methods=['GET', 'POST'])
def add_entry():
    if request.method == 'POST':
        entry = Entry(
            morning_routine=request.form.get('morning_routine'),
            evening_routine=request.form.get('evening_routine'),
            skin_condition=request.form.get('skin_condition'),
            notes=request.form.get('notes')
        )
        db.session.add(entry)
        db.session.commit()
        flash('Entry added successfully!', 'success')
        return redirect(url_for('index'))
    return render_template('add_entry.html')

if __name__ == '__main__':
    app.run(debug=True)
