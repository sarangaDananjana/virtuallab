import os
import sys
import csv
import django
import argparse
from dotenv import load_dotenv


def main():
    """
    Main function to load Django, connect to the DB, and import quizzes.
    """

    parser = argparse.ArgumentParser(
        description='Import quizzes from a CSV file.')
    parser.add_argument(
        '--env',
        choices=['dev', 'prod'],
        default='dev',
        help='The environment to run against (dev or prod). This determines which .env file to load.'
    )
    args = parser.parse_args()

    # --- 1. Load Environment Variables ---
    env_file_name = f'.env.{args.env}'

    # Construct the path to the parent directory
    env_file_path = os.path.join('..', env_file_name)

    print(f"Loading environment variables from {env_file_path}...")

    if not load_dotenv(env_file_path):
        print(f"Error: {env_file_path} file not found.")
        print("Please make sure the file exists in the parent directory.")
        return

    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        print(f"Error: DATABASE_URL not found in {env_file_path}.")
        return

    # --- 2. Bootstrap Django Environment ---
    print("Adding current directory to Python path...")
    sys.path.append(os.path.abspath('.'))

    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'virtuallabshop.settings')

    try:
        print("Initializing Django...")
        django.setup()
        print("Django initialized. Connecting to database...")
    except Exception as e:
        print(f"Error initializing Django: {e}")
        print("Please check the following:")
        print("1. Is 'virtuallabshop.settings' the correct path?")
        print(
            "2. Is your project folder (the one with settings.py) named 'virtuallabshop'?")
        return

    # --- 3. Import Models (MUST be after django.setup()) ---
    try:
        from shop.models import Quiz, Question, Choice
        from django.db import transaction
    except ImportError:
        print("\n--- ERROR ---")
        print("Could not import models from 'shop.models'.")
        print("Please change 'shop.models' in this script")
        print("to the correct app name (e.g., 'core.models').")
        print("-------------\n")
        return

    # --- 4. Run the Import Logic ---
    csv_file_path = 'quizzes.csv'
    question_order_counter = {}
    quizzes_created = 0
    questions_created = 0
    choices_created = 0

    try:
        with transaction.atomic():
            print(f"Opening {csv_file_path}...")
            with open(csv_file_path, mode='r', encoding='utf-8') as file:
                reader = csv.DictReader(file)

                for row_number, row in enumerate(reader, 1):

                    # --- THIS IS THE FIX ---
                    # Skip empty rows (which DictReader reads as all None)
                    if not row or not row.get('quiz_number'):
                        print(
                            f"Skipping empty or invalid row at line {row_number}...")
                        continue
                    # --- END OF FIX ---

                    try:
                        # 1. Get or Create the Quiz
                        quiz, created = Quiz.objects.get_or_create(
                            quiz_number=int(row['quiz_number']),
                            defaults={'title': row['quiz_title']}
                        )
                        if created:
                            quizzes_created += 1
                            question_order_counter[quiz.id] = 0

                        # 2. Get the current order for this question
                        current_order = question_order_counter.get(
                            quiz.id, 0) + 1
                        question_order_counter[quiz.id] = current_order

                        # 3. Create the Question
                        question = Question.objects.create(
                            quiz=quiz,
                            question_text=row['question_text'],
                            order=current_order
                        )
                        questions_created += 1

                        # 4. Create the Choices
                        choices_to_create = []
                        correct_index = int(row['correct_choice'])

                        for i in range(1, 5):
                            choice_text = row.get(f'choice_{i}')
                            if not choice_text:
                                continue

                            is_correct = (i == correct_index)

                            choices_to_create.append(
                                Choice(
                                    question=question,
                                    choice_text=choice_text,
                                    is_correct=is_correct
                                )
                            )

                        Choice.objects.bulk_create(choices_to_create)
                        choices_created += len(choices_to_create)

                    except Exception as e:
                        # This will report any error for a specific row
                        print(f"Error processing row {row_number}: {e}")
                        print(f"Row data: {row}")

        print("\n--- SUCCESS! ---")
        print(f"Import complete for '{args.env}' environment.\n"
              f"- {quizzes_created} new quizzes created.\n"
              f"- {questions_created} new questions created.\n"
              f"- {choices_created} new choices created.\n")

    except FileNotFoundError:
        print(f"Error: {csv_file_path} not found.")
        print("Please make sure 'quizzes.csv' is in the same directory.")
    except Exception as e:
        print(f"\n--- ERROR ---")
        print(f"An error occurred: {e}")
        print("The database transaction has been rolled back.")


if __name__ == "__main__":
    main()
