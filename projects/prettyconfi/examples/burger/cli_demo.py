#!/usr/bin/env python3
"""Burger Builder CLI — prettyconfi demo."""

from pathlib import Path

from prettyconfi import load_schema, compose, CLIRunner, StopSave, to_env, from_env


def main():
    schema_path = Path(__file__).parent / "schema.toml"
    save_path = Path(__file__).parent / "burger_order.env"

    schema = load_schema(schema_path)
    composed = compose([schema])

    # Load previous save if exists
    seed = {}
    if save_path.exists():
        seed = from_env(save_path)
        print(f"\n  Loaded saved order from {save_path.name}")
        print("  (Your previous choices are pre-filled)\n")

    runner = CLIRunner(composed, seed=seed)

    try:
        answers = runner.run()
    except StopSave as e:
        to_env(e.answers, save_path)
        print(f"\n  Order saved to {save_path.name} — come back anytime!")
        return
    except KeyboardInterrupt:
        print("\n  Bye!")
        return

    # Show the order
    print("\n" + "=" * 40)
    print("  YOUR BURGER ORDER")
    print("=" * 40)

    name = answers.get("CUSTOMER_NAME", "Anonymous")
    print(f"\n  Order for: {name}")
    print(f"  Bun: {answers.get('BUN_TYPE', '?')} {'(toasted)' if answers.get('BUN_TOASTED') else ''}")
    print(f"  Patty: {answers.get('PATTY_TYPE', '?')}", end="")
    if answers.get("PATTY_DONENESS"):
        print(f" ({answers['PATTY_DONENESS']})", end="")
    print()

    if answers.get("ADD_CHEESE"):
        print(f"  Cheese: {answers.get('CHEESE_TYPE', 'cheddar')}")

    toppings = []
    for key, label in [("ADD_PICKLES", "Pickles"), ("ADD_ONIONS", "Onions"),
                        ("ADD_TOMATO", "Tomato"), ("ADD_LETTUCE", "Lettuce"),
                        ("ADD_JALAPENOS", "Jalapenos")]:
        if answers.get(key):
            toppings.append(label)
    if toppings:
        print(f"  Toppings: {', '.join(toppings)}")

    sauces = []
    for key, label in [("SAUCE_KETCHUP", "Ketchup"), ("SAUCE_MUSTARD", "Mustard"),
                        ("SAUCE_MAYO", "Mayo"), ("SAUCE_BBQ", "BBQ"),
                        ("SAUCE_SPECIAL", "Special Sauce")]:
        if answers.get(key):
            sauces.append(label)
    if sauces:
        print(f"  Sauces: {', '.join(sauces)}")

    if answers.get("ADD_FRIES"):
        fries_sauces = []
        if answers.get("FRIES_SAUCE_KETCHUP"):
            fries_sauces.append("ketchup")
        if answers.get("FRIES_SAUCE_MAYO"):
            fries_sauces.append("mayo")
        extra = f" with {' & '.join(fries_sauces)}" if fries_sauces else ""
        print(f"  Fries: {answers.get('FRIES_SIZE', 'medium')}{extra}")

    if answers.get("ADD_DRINK"):
        drink = answers.get("DRINK_TYPE", "?")
        if drink == "milkshake":
            drink = f"{answers.get('MILKSHAKE_FLAVOR', 'vanilla')} milkshake"
        print(f"  Drink: {drink} ({answers.get('DRINK_SIZE', 'medium')})")

    print("\n" + "=" * 40)

    # Save
    to_env(answers, save_path)
    print(f"  Saved to {save_path.name}")


if __name__ == "__main__":
    main()
