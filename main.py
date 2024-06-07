import asyncio
from bs4 import BeautifulSoup
from playwright.async_api import Playwright, async_playwright
from tabulate import tabulate


async def run(playwright: Playwright, *, url: str, course: str) -> str:
    # Basic navigation to desired page.
    browser = await playwright.chromium.launch(headless=True)
    page = await browser.new_page()
    await page.goto(url)

    # Inputting desired class into testudo
    # course input: course-id-input
    await page.fill('#course-id-input', course)
    await page.press('#course-id-input', 'Enter')

    # Get the class's html information
    try:
        html = page.locator('xpath=/html/body/div[2]/div/div[2]/div[2]/div[1]/div[2]/div/div[2]/div/div/div[2]')
        div_html = await html.inner_html()
        return div_html
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
    prereqs = insert_newlines(prereqs, 75)

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
        f.write(tabulate(class_details, headers=["Field", "Value"], tablefmt="grid"))
        f.write("\n\nSection Details\n")
        f.write(tabulate(section_details, headers="firstrow", tablefmt="grid"))


async def main() -> None:
    # Use async_playwright context manager to close the Playwright instance
    # automatically.
    class_id = input('Enter a class: ')
    async with async_playwright() as playwright:
        html = await run(playwright, url='https://app.testudo.umd.edu/soc/', course=class_id)
        class_html = BeautifulSoup(html, 'html.parser')

    class_info = get_class_info(class_html)
    display_class_info(class_info, class_id)


def insert_newlines(string: str, interval: int) -> str:
    return '-\n'.join(string[i:i + interval] for i in range(0, len(string), interval))


if __name__ == '__main__':
    asyncio.run(main())
