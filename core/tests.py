import ast
import asyncio
from pathlib import Path

import discord
from django.conf import settings
from django.test import SimpleTestCase


class DiscordDuesRegistrationModalTests(SimpleTestCase):
    def test_modal_renders_term_select_and_uses_selected_redirect(self):
        source = (Path(settings.BASE_DIR) / "discord_bot.py").read_text()
        tree = ast.parse(source)
        modal_node = next(
            node
            for node in tree.body
            if isinstance(node, ast.ClassDef) and node.name == "AccountCreationModalForPayCommand"
        )
        pay_node = next(node for node in tree.body if isinstance(node, ast.AsyncFunctionDef) and node.name == "pay")
        self.assertIn("ctx.send_modal", ast.unparse(pay_node))

        presented = []

        class AccountCreationView:
            def __init__(self, *args, **kwargs):
                self.args = args
                self.kwargs = kwargs

            async def present(self, interaction, *, content):
                presented.append((self, interaction, content))
                if interaction.message is not None:
                    await interaction.response.edit_message(content=content, view=self)
                else:
                    await interaction.response.send_message(content=content, view=self, ephemeral=True)

        namespace = {
            "discord": discord,
            "is_valid_net_id": lambda net_id: net_id == "abc123456",
            "AccountCreationView": AccountCreationView,
            "Term": object,
            "ORG_NAME": "Comet Robotics",
        }
        exec(compile(ast.Module(body=[modal_node], type_ignores=[]), "discord_bot.py", "exec"), namespace)
        modal_class = namespace["AccountCreationModalForPayCommand"]

        class Response:
            def __init__(self):
                self.messages = []
                self.edits = []
                self.modals = []

            async def send_message(self, *args, **kwargs):
                self.messages.append((args, kwargs))

            async def edit_message(self, *args, **kwargs):
                self.edits.append((args, kwargs))

            async def send_modal(self, modal):
                self.modals.append(modal)

        class User:
            id = 42

        class Interaction:
            def __init__(self, message=None):
                self.user = User()
                self.response = Response()
                self.data = {}
                self.message = message

        class FakeTerm:
            name = "Fall 2026"

            def get_pay_path(self):
                return "/payments/1/pay/"

        async def submit_modal():
            terms = [FakeTerm()]
            modal = modal_class(42, terms)
            self.assertIsInstance(modal, discord.ui.DesignerModal)
            self.assertIsInstance(modal.children[0], discord.ui.TextDisplay)
            self.assertIsInstance(modal.children[2].item, discord.ui.Select)
            self.assertEqual(modal.to_components()[2]["component"]["type"], 3)

            interaction = Interaction()
            modal._refresh(
                interaction,
                [
                    {"type": 10, "content": "intro"},
                    {"component": {"custom_id": modal.net_id.custom_id, "value": "abc123456"}},
                    {"component": {"custom_id": modal.term.custom_id, "values": ["/payments/1/pay/"]}},
                ],
            )
            await modal.callback(interaction)

            view, _, content = presented[0]
            self.assertIn("`abc123456`", content)
            self.assertEqual(view.args, ("abc123456", 42))
            self.assertEqual(view.kwargs["after_registration_redirect_destination"], "/payments/1/pay/")
            self.assertIs(view.kwargs["parent"], modal)

            (_, response_kwargs), = interaction.response.messages
            self.assertTrue(response_kwargs["ephemeral"])
            self.assertIs(response_kwargs["view"], view)

            # Go back re-presents the same modal instance (no state rebuild).
            go_back_interaction = Interaction(message=object())
            await view.kwargs["parent"].present(go_back_interaction)
            self.assertEqual(go_back_interaction.response.modals, [modal])
            self.assertTrue(any(option.default for option in modal.term.options if option.value == "/payments/1/pay/"))

            # Re-submit after go-back updates the existing confirmation message.
            presented.clear()
            interaction = Interaction(message=object())
            modal._refresh(
                interaction,
                [
                    {"type": 10, "content": "intro"},
                    {"component": {"custom_id": modal.net_id.custom_id, "value": "abc123456"}},
                    {"component": {"custom_id": modal.term.custom_id, "values": ["/payments/1/pay/"]}},
                ],
            )
            await modal.callback(interaction)
            self.assertEqual(interaction.response.messages, [])
            (_, edit_kwargs), = interaction.response.edits
            self.assertEqual(edit_kwargs["view"].args, ("abc123456", 42))
            self.assertIs(edit_kwargs["view"].kwargs["parent"], modal)

        asyncio.run(submit_modal())
