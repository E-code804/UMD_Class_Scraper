import asyncio
from bs4 import BeautifulSoup
from playwright.async_api import Playwright, async_playwright
from tabulate import tabulate


async def select_semester(options):
    semester_dict = {}
    print("Available semesters:")

    for i, option in enumerate(options):
        value = await option.get_attribute('value')
        semester = await option.inner_text()
        semester_dict[i] = (value, semester)
        print(f"Enter {i} for {semester}")

    # Get user input
    semester_index = int(input("Select a semester: "))
    while semester_index not in semester_dict:
        semester_index = int(input("Invalid number inputted, please select a valid number between 0-3: "))

    selected_semester_value = semester_dict[semester_index][0]
    return selected_semester_value


async def run(playwright: Playwright, *, url: str, course: str) -> str:
    # Basic navigation to desired page.
    browser = await playwright.chromium.launch(headless=False)
    page = await browser.new_page()
    await page.goto(url)

    # Inputting desired class into testudo
    # course input: course-id-input
    await page.fill('#course-id-input', course)
    select_element = page.locator("#term-id-input")
    option_elements = await select_element.locator('option').all()
    # Run method to display all semester & select one.
    option_value = await select_semester(option_elements)
    await select_element.select_option(value=option_value)

    await page.press('#course-id-input', 'Enter')

    # Get the class's html information
    try:
        html = await page.inner_html('body')
        return html
    except Exception as e:
        print(f"Error: {e}")
        return "Not found."
    finally:
        await browser.close()


def get_class_info(html):
    # Get class name
    class_name = html.find('span', class_='course-title').text
    # Get # credits
    credits = html.find('span', class_='course-min-credits').text
    # Get prereqs & description
    course_text = html.find_all('div', class_='approved-course-text')

    prereqs = course_text[0].text
    prereqs = insert_newlines(prereqs, 75)  # Remove "Prerequisite: " from start

    description = course_text[1].text
    description = insert_newlines(description, 75)
    # Get all the sections - Location, prof, section, time, seats
    sections = html.find_all('div', class_='section delivery-f2f')
    sections_info = process_sections(sections)

    return {
        'class_name': class_name,
        'credits': credits,
        'prereqs': prereqs,
        'description': description,
        'sections': sections_info
    }


def process_sections(sections):
    section_dict = {}

    for section in sections:
        section_number = section.find('span', class_='section-id').text.strip()
        professor = section.find('span', class_='section-instructor').text

        days = section.find('span', class_='section-days').text
        start = section.find('span', class_='class-start-time').text
        end = section.find('span', class_='class-start-time').text
        times = f"{days}: {start}-{end}"

        building = section.find('span', class_='building-code').text
        room_num = section.find('span', class_='class-room').text
        location = ' '.join([building, room_num])

        total_seats = section.find('span', class_='total-seats-count').text
        open_seats = section.find('span', class_='open-seats-count').text
        waitlist_seats = section.find('span', class_='waitlist-count').text
        seat_info = f"Total: {total_seats}, Open: {open_seats}, Waitlist: {waitlist_seats}"

        section_dict[section_number] = {
            'professor': professor,
            'times': times,
            'location': location,
            'seat_info': seat_info
        }

    return section_dict


def display_class_info(info, class_id):
    class_details = [
        ["Class Name", info['class_name']],
        ["Credits", info['credits']],
        ["Prerequisites", info['prereqs']],
        ["Description", info['description']]
    ]

    section_details = [["Section", "Professor", "Times", "Location", "Seat Info"]]
    for sec_num, sec_info in info['sections'].items():
        section_details.append([
            sec_num,
            sec_info['professor'],
            sec_info['times'],
            sec_info['location'],
            sec_info['seat_info']
        ])

    with open(f"{class_id}_info.txt", 'w') as f:
        f.write("Class Details\n")
        f.write(tabulate(class_details, tablefmt="grid"))
        f.write("\n\nSection Details\n")
        f.write(tabulate(section_details, headers="firstrow", tablefmt="grid"))


async def main() -> None:
    # Use async_playwright context manager to close the Playwright instance
    # automatically.
    url = 'https://app.testudo.umd.edu/soc/'
    class_id = input('Enter a class: ')

    async with async_playwright() as playwright:
        html = await run(playwright, url=url, course=class_id)
        class_html = BeautifulSoup(html, 'html.parser')

    class_info = get_class_info(class_html)
    display_class_info(class_info, class_id)


def insert_newlines(string: str, interval: int) -> str:
    return '-\n'.join(string[i:i + interval] for i in range(0, len(string), interval))


if __name__ == '__main__':
    asyncio.run(main())
