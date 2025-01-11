import json
import os
import time
from flask import Flask, render_template, request, redirect, url_for, flash
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.trace import SpanKind, StatusCode
from opentelemetry import metrics
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import (ConsoleMetricExporter, PeriodicExportingMetricReader)

# Flask App Initialization
app = Flask(__name__)
app.secret_key = 'secret'
COURSE_FILE = 'course_catalog.json'

# OpenTelemetry Setup
resource = Resource.create({"service.name": "course-catalog-service"})
trace.set_tracer_provider(TracerProvider(resource=resource))
tracer = trace.get_tracer(__name__)
jaeger_exporter = JaegerExporter(
    agent_host_name="localhost",
    agent_port=6831,
)
span_processor = BatchSpanProcessor(jaeger_exporter)
trace.get_tracer_provider().add_span_processor(span_processor)
console_exporter = ConsoleSpanExporter()
# trace.get_tracer_provider().add_span_processor(BatchSpanProcessor(console_exporter))

# Setting up metrics - counters
metric_reader = PeriodicExportingMetricReader(ConsoleMetricExporter(), export_interval_millis=5000)
provider = MeterProvider(metric_readers=[metric_reader])
# Sets the global default meter provider
metrics.set_meter_provider(provider)
# Creates a meter from the global meter provider
meter = metrics.get_meter("main.meter")

new_course_counter = meter.create_counter("new_course_counter", unit="requests", description="Number of new courses added")
error_counter = meter.create_counter("error_counter", unit="requests", description="Number of errors")
page_access_counter = meter.create_counter("page_access_counter", unit="requests", description="Number of page accesses")

timing_histogram = meter.create_histogram("timing_histogram", unit="ns", description="Request timing histogram")

# Utility Functions
def load_courses():
    """Load courses from the JSON file."""
    if not os.path.exists(COURSE_FILE):
        return []  # Return an empty list if the file doesn't exist
    with open(COURSE_FILE, 'r') as file:
        with create_span("load-courses-span") as span:
            span.add_event("Loaded Courses from JSON file")
            span.set_status(StatusCode.OK)
            return json.load(file)


def save_courses(data):
    """Save new course data to the JSON file."""
    courses = load_courses()  # Load existing courses
    courses.append(data)  # Append the new course
    with open(COURSE_FILE, 'w') as file:
        json.dump(courses, file, indent=4)
        new_course_counter.add(1)

def create_span(name, Kind=SpanKind.SERVER):
    return tracer.start_as_current_span(name, kind=Kind)

def span_attributes(span):
    span.set_attribute("http.method", request.method)
    span.set_attribute("http.url", request.url)
    span.set_attribute("peer.ip", request.remote_addr)
    span.set_attribute("http.user_agent", request.headers.get('User-Agent', 'Unknown'))

# Routes
@app.route('/')
def index():
    with create_span("index-span") as span:
        span_attributes(span)
        span.add_event("Rendered Course Information Index Page")
        span.set_attribute("http.status_code", 200)
        span.set_status(StatusCode.OK)
        response = render_template('index.html')
        page_access_counter.add(1, {"page": "index"})
        return response, 200



@app.route('/catalog')
def course_catalog():
    with create_span("catalog-span") as span:
        s_time = time.time_ns()
        span_attributes(span)
        try:
            courses = load_courses()
        except Exception as e:
            span.set_status(StatusCode.ERROR)
            span.add_event("Unable to load course data. Error: " + str(e))
            span.set_attribute("http.status_code", 505)
            error_counter.add(1)
            return redirect(url_for('index'))

        course_names = ", ".join(course['code'] + ' ' + course['name'] for course in courses)
        span.add_event(f"Loaded Courses named: {course_names}")

        response = render_template('course_catalog.html', courses=courses)
        span.add_event("Rendered Course Catalog")
        span.set_status(StatusCode.OK)
        span.set_attribute("http.status_code", 200)
        t_time = time.time_ns() - s_time
        timing_histogram.record(t_time, {"page": "catalog"})
        page_access_counter.add(1, {"page": "catalog"})
        return response, 200


@app.route('/add_course', methods=['GET', 'POST'])
def add_course():
    with create_span("add-course-span") as span:
        span_attributes(span)
        if request.method == 'POST':
            s_time = time.time_ns()
            course = {
                'code': request.form['code'],
                'name': request.form['name'],
                'instructor': request.form['instructor'],
                'semester': request.form['semester'],
                'schedule': request.form['schedule'],
                'classroom': request.form['classroom'],
                'prerequisites': request.form['prerequisites'],
                'grading': request.form['grading'],
                'description': request.form['description']
            }

            span.add_event("Form Submissions Recorded")

            # form validation
            if any(course[key].strip() == '' for key in list(course.keys())):
                flash(f"You have left some fields empty, Please fill up!!")
                span.add_event("Malformed Form Submissions")
                span.set_status(StatusCode.ERROR)
                span.set_attribute("http.status_code", 400)
                error_counter.add(1)
                return render_template('add_course.html')

            span.add_event("Submissions Validated Successfully")
            save_courses(course)
            span.add_event("New Course Added: " + course['code'] + ' ' + course['name'])
            flash(f"Course '{course['name']}' added successfully!", "success")
            t_time = time.time_ns() - s_time
            timing_histogram.record(t_time, {"page": "add-course"})
            new_course_counter.add(1)

            span.set_status(StatusCode.OK)
            span.set_attribute("http.status_code", 200)
            return redirect(url_for('course_catalog'))

        response = render_template('add_course.html')
        span.add_event("Rendered Add Course page")
        span.set_status(StatusCode.OK)
        span.set_attribute("http.status_code", 200)
        return response, 200


@app.route('/course/<code>')
def course_details(code):
    with create_span("course-details-span") as span:
        span_attributes(span)
        courses = load_courses()

        course = next((course for course in courses if course['code'] == code), None)
        if not course:
            span.add_event("Requested Course " + code + " Not found")
            flash(f"No course found with code '{code}'.", "error")
            span.set_status(StatusCode.ERROR)
            span.set_attribute("http.status_code", 400)
            return redirect(url_for('course_catalog'))

        response = render_template('course_details.html', course=course)
        span.add_event("Requested Course " + code + " details rendered")

        span.set_status(StatusCode.OK)
        span.set_attribute("http.status_code", 200)
        return response, 200


@app.route("/manual-trace")
def manual_trace():
    # Start a span manually for custom tracing
    with tracer.start_as_current_span("manual-span", kind=SpanKind.SERVER) as span:
        span.set_attribute("http.method", request.method)
        span.set_attribute("http.url", request.url)
        span.add_event("Processing request")
        return "Manual trace recorded!", 200


@app.route("/auto-instrumented")
def auto_instrumented():
    # Automatically instrumented via FlaskInstrumentor
    return "This route is auto-instrumented!", 200


if __name__ == '__main__':
    app.run(debug=True)
