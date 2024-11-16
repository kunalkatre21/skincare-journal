from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os
from dotenv import load_dotenv
from werkzeug.utils import secure_filename
from PIL import Image
import uuid
import random

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'postgresql://localhost/skincare_journal')
app.config['UPLOAD_FOLDER'] = 'static/uploads'
db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    inspired_by_link = db.Column(db.String(100))  # Share link that brought them
    transformations = db.relationship('TransformationStory', backref='user', lazy=True)

class TransformationStory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # A/B Test: Some users start with just before photo
    test_group = db.Column(db.String(1))  # 'A' for before-only, 'B' for before-and-after
    
    # Core transformation data
    before_photo = db.Column(db.String(200))
    after_photo = db.Column(db.String(200))
    routine_summary = db.Column(db.String(500))
    
    # Growth metrics
    share_link = db.Column(db.String(8), unique=True)
    views = db.Column(db.Integer, default=0)
    inspired_joins = db.Column(db.Integer, default=0)

@app.route('/')
def index():
    # Show top transformations with both before/after photos
    top_stories = TransformationStory.query\
        .filter(TransformationStory.after_photo.isnot(None))\
        .order_by(TransformationStory.inspired_joins.desc())\
        .limit(6)\
        .all()
    return render_template('index.html', transformations=top_stories)

@app.route('/start', methods=['GET', 'POST'])
def start_journey():
    if request.method == 'POST':
        # Randomly assign A/B test group
        test_group = random.choice(['A', 'B'])
        
        story = TransformationStory(
            user_id=1,  # Placeholder until auth
            test_group=test_group,
            routine_summary=request.form.get('routine_summary'),
            share_link=str(uuid.uuid4())[:8]
        )
        
        if 'before_photo' in request.files:
            photo = request.files['before_photo']
            if photo and allowed_file(photo.filename):
                filename = f"before_{story.share_link}_{secure_filename(photo.filename)}"
                save_photo(photo, filename)
                story.before_photo = filename
        
        # Group B users upload both photos immediately
        if test_group == 'B' and 'after_photo' in request.files:
            photo = request.files['after_photo']
            if photo and allowed_file(photo.filename):
                filename = f"after_{story.share_link}_{secure_filename(photo.filename)}"
                save_photo(photo, filename)
                story.after_photo = filename
        
        db.session.add(story)
        db.session.commit()
        
        return redirect(url_for('view_story', share_link=story.share_link))
    
    # Track which share link brought them here
    inspired_by = request.args.get('ref')
    if inspired_by:
        session['inspired_by'] = inspired_by
    
    return render_template('start_journey.html', 
                         inspired_by=session.get('inspired_by'))

@app.route('/s/<share_link>')
def view_story(share_link):
    story = TransformationStory.query.filter_by(share_link=share_link).first_or_404()
    story.views += 1
    db.session.commit()
    
    return render_template('view_story.html', 
                         story=story,
                         days=days_since(story.created_at))

@app.route('/update/<share_link>', methods=['POST'])
def update_after_photo(share_link):
    story = TransformationStory.query.filter_by(share_link=share_link).first_or_404()
    
    if 'after_photo' in request.files:
        photo = request.files['after_photo']
        if photo and allowed_file(photo.filename):
            filename = f"after_{story.share_link}_{secure_filename(photo.filename)}"
            save_photo(photo, filename)
            story.after_photo = filename
            db.session.commit()
            flash('Your after photo has been added!', 'success')
    
    return redirect(url_for('view_story', share_link=share_link))

@app.route('/inspired/<share_link>')
def track_inspired(share_link):
    story = TransformationStory.query.filter_by(share_link=share_link).first_or_404()
    story.inspired_joins += 1
    db.session.commit()
    return redirect(url_for('start_journey', ref=share_link))

def save_photo(photo_file, filename):
    img = Image.open(photo_file)
    img.thumbnail((800, 800))
    img.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg'}

def days_since(date):
    return (datetime.utcnow() - date).days

# Add template context processor
@app.context_processor
def utility_processor():
    return dict(days_since=days_since)

with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)
