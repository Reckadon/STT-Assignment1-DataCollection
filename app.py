###############################
## Import Required Libraries ##
###############################
import json
import logging
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

# Flask setup
app = Flask(__name__)
app.secret_key = 'secret'
COURSE_FILE = 'course_catalog.json'


#########################
## OpenTelemetry Setup ##
#########################
resource = Resource.create({"service.name": "course-catalog-service"})
trace.set_tracer_provider(TracerProvider(resource=resource))
tracer = trace.get_tracer(__name__)

# Jaeger Exporter
jaeger_exporter = JaegerExporter(
    agent_host_name="localhost",
    agent_port=6831,
)
span_processor = BatchSpanProcessor(jaeger_exporter)
trace.get_tracer_provider().add_span_processor(span_processor)

# Console Exporter
console_exporter = ConsoleSpanExporter()
# trace.get_tracer_provider().add_span_processor(BatchSpanProcessor(console_exporter))

# Metrics Configuration
metric_reader = PeriodicExportingMetricReader(ConsoleMetricExporter(), export_interval_millis=5000)
provider = MeterProvider(metric_readers=[metric_reader])
metrics.set_meter_provider(provider)
meter = metrics.get_meter("main.meter")

# Defining Metrics
new_course_counter = meter.create_counter("new_course_counter", unit="requests", description="Number of new courses added")
error_counter = meter.create_counter("error_counter", unit="requests", description="Number of errors")
page_access_counter = meter.create_counter("page_access_counter", unit="requests", description="Number of page accesses")
timing_histogram = meter.create_histogram("timing_histogram", unit="ns", description="Request timing histogram")


##############################
## Structured Logging Setup ##
##############################
class JsonFormatter(logging.Formatter):
    def format(self, record):
        """format log messages as JSON"""
        log_entry = {
            'timestamp': self.formatTime(record),
            'level': record.levelname,
            'message': record.getMessage(),
            'logger': record.name,
            'filename': record.pathname,
            'line': record.lineno
        }
        return json.dumps(log_entry, indent=4)

# Configure Logging
handler = logging.FileHandler('application.log')
handler.setFormatter(JsonFormatter())
logger = logging.getLogger('Custom JSON Logger')
logger.setLevel(logging.INFO)
logger.addHandler(handler)


#######################
## Utility Functions ##
#######################
def load_courses():
    """load courses from JSON file"""
    if not os.path.exists(COURSE_FILE):
        return []  # Return an empty list if the file doesn't exist
    with open(COURSE_FILE, 'r') as file:
        with create_span("load-courses-span") as span:
            span.add_event("Loaded Courses from JSON file")
            span.set_status(StatusCode.OK)
            return json.load(file)


def save_courses(data):
    """save the course data to JSON file"""
    courses = load_courses()  # Load existing courses
    courses.append(data)  # Append the new course
    with open(COURSE_FILE, 'w') as file:
        json.dump(courses, file, indent=4)
        new_course_counter.add(1)


def create_span(name, Kind=SpanKind.SERVER):
    """helper function for creating a tracing span"""
    return tracer.start_as_current_span(name, kind=Kind)


def span_attributes(span):
    """add standard attributes to the tracing span"""
    span.set_attribute("http.method", request.method)
    span.set_attribute("http.url", request.url)
    span.set_attribute("peer.ip", request.remote_addr)
    span.set_attribute("http.user_agent", request.headers.get('User-Agent', 'Unknown'))



##################
## Flask Routes ##
##################
@app.route('/')
def index():
    """renders the index page"""
    with create_span("index-span") as span:
        span_attributes(span)
        span.add_event("Rendered Course Information Index Page")   # add an event to the span, which will be logged
        span.set_status(StatusCode.OK)  # gives a status code to the span
        logger.info("Page Rendered: Index")
        response = render_template('index.html')
        page_access_counter.add(1, {"page": "index"})  # the second argument - attributes, helps to identify and segregate metrics in a single counter
        return response, 200


@app.route('/catalog')
def course_catalog():
    """displays the course catalog"""
    with create_span("catalog-span") as span:
        s_time = time.time_ns()
        span_attributes(span)
        try:
            courses = load_courses()
        except Exception as e:
            span.set_status(StatusCode.ERROR)
            span.add_event("Error loading course data: " + str(e))
            error_counter.add(1)
            return redirect(url_for('index'))

        response = render_template('course_catalog.html', courses=courses)
        span.set_status(StatusCode.OK)
        timing_histogram.record(time.time_ns() - s_time, {"page": "catalog"})
        page_access_counter.add(1, {"page": "catalog"})
        logger.info("Page Rendered: Course Catalog")
        return response, 200


@app.route('/add_course', methods=['GET', 'POST'])
def add_course():
    """adds a new course to the catalog"""
    with create_span("add-course-span") as span:
        span_attributes(span)
        if request.method == 'POST':
            s_time = time.time_ns()
            course = {key: request.form[key] for key in request.form}
            if any(value.strip() == '' for value in course.values()):
                flash("Please fill all required fields", "warning")
                span.set_status(StatusCode.ERROR)
                error_counter.add(1)
                return render_template('add_course.html')

            save_courses(course)
            flash(f"Course '{course['name']}' added successfully!", "success")
            logger.info(f"Course Added: {course['code']} {course['name']}")
            return redirect(url_for('course_catalog'))

        logger.info("Page Rendered: Add Course")
        return render_template('add_course.html')


@app.route('/course/<code>')
def course_details(code):
    """displays the details of a specific course"""
    with create_span("course-details-span") as span:
        span_attributes(span)
        courses = load_courses()
        course = next((course for course in courses if course['code'] == code), None)
        if not course:
            flash(f"No course found with code '{code}'", "error")
            logger.error(f"Course {code} Not Found")
            return redirect(url_for('course_catalog'))

        logger.info(f"Page Rendered: Course Details - {code}")
        return render_template('course_details.html', course=course)

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
