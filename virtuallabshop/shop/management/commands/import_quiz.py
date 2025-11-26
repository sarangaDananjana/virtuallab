import csv
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.translation import gettext_lazy as _
# Import your models.
# Make sure to change 'your_app_name' to the actual name of your app
from .models import Quiz, Question, Choice


class Command(BaseCommand):
    help = 'Imports quizzes, questions, and choices from a specified CSV file.'

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str,
                            help='The path to the CSV file to import.')

    @transaction.atomic
    def handle(self, *args, **options):
        csv_file_path = options['csv_file']
        self.stdout.write(self.style.NOTICE(
            f'Starting import from {csv_file_path}...'))

        # Keep track of created items
        quizzes_created = 0
        questions_created = 0
        choices_created = 0

        try:
            with open(csv_file_path, mode='r', encoding='utf-8') as file:
                reader = csv.DictReader(file)

                for row in reader:
                    try:
                        # 1. Get or Create the Quiz
                        quiz, created = Quiz.objects.get_or_create(
                            quiz_number=int(row['quiz_number']),
                            defaults={
                                'title': row['quiz_title'],
                                'time_limit_minutes': 15  # Default, you can change this
                            }
                        )
                        if created:
                            quizzes_created += 1

                        # 2. Create the Question
                        question = Question.objects.create(
                            quiz=quiz,
                            question_text=row['question_text'],
                            hint=row['hint']
                            # 'order' can be set automatically or based on CSV
                        )
                        questions_created += 1

                        # 3. Create the Choices
                        choices_to_create = []
                        correct_index = int(row['correct_choice'])

                        for i in range(1, 5):
                            choice_text = row.get(f'choice_{i}')
                            rationale = row.get(f'rationale_{i}')

                            if not choice_text:
                                continue  # Skip if choice is empty

                            is_correct = (i == correct_index)

                            choices_to_create.append(
                                Choice(
                                    question=question,
                                    choice_text=choice_text,
                                    is_correct=is_correct,
                                    # We add rationale here if your model has it
                                    # rationale=rationale  # Uncomment if you add 'rationale' to your Choice model
                                )
                            )

                        Choice.objects.bulk_create(choices_to_create)
                        choices_created += len(choices_to_create)

                    except Exception as e:
                        self.stderr.write(self.style.ERROR(
                            f'Error processing row {reader.line_num}: {e}'))
                        self.stderr.write(
                            self.style.WARNING(f'Row data: {row}'))

        except FileNotFoundError:
            raise CommandError(f'File "{csv_file_path}" does not exist.')
        except Exception as e:
            raise CommandError(f'An unexpected error occurred: {e}')

        self.stdout.write(self.style.SUCCESS(
            '-------------------------------------------------\n'
            f'Successfully completed import!\n'
            f'- {quizzes_created} new quizzes created.\n'
            f'- {questions_created} new questions created.\n'
            f'- {choices_created} new choices created.\n'
            '-------------------------------------------------'
        ))
