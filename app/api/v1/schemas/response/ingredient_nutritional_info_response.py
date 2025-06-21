"""Contains common schema definitions for nutritional information."""

from decimal import Decimal
from typing import TYPE_CHECKING, Any

from pydantic import Field

from app.api.v1.schemas.base_schema import BaseSchema
from app.api.v1.schemas.common.ingredient import Quantity
from app.enums.allergy import Allergy
from app.enums.ingredient_unit_enum import IngredientUnitEnum
from app.utils.unit_converter import UnitConverter

if TYPE_CHECKING:
    from app.db.models.nutritional_info_models.nutritional_info import NutritionalInfo


def _combine_string_optional(a: str | None, b: str | None) -> str | None:
    """Combine two optional strings, preferring the first non-None value.

    Args:
        a (str | None): First string value.
        b (str | None): Second string value.

    Returns:
        str | None: The first non-None value, or None if both are None.
    """
    return a or b


def _combine_nutriscore_grades_optional(
    grade_a: str | None,
    grade_b: str | None,
) -> str | None:
    """Combine two nutriscore grades by taking the worst (highest) grade.

    Args:
        grade_a (str | None): First nutriscore grade.
        grade_b (str | None): Second nutriscore grade.

    Returns:
        str | None: The worst grade, or None if both are None.
    """
    if not grade_a and not grade_b:
        return None
    if not grade_a:
        return grade_b
    if not grade_b:
        return grade_a

    # Return the worst grade (A is best, E is worst)
    grade_order = {"A": 1, "B": 2, "C": 3, "D": 4, "E": 5}

    # Default to E if grade not recognized
    grade_a_val = grade_order.get(grade_a.upper(), 5)
    grade_b_val = grade_order.get(grade_b.upper(), 5)

    # Return the worse grade
    if grade_a_val >= grade_b_val:
        return grade_a.upper()
    return grade_b.upper()


def _sum_decimal_optional(
    a: Decimal | None,
    b: Decimal | None,
    precision: str = "0.001",
) -> Decimal | None:
    """Add two optional decimals with specified precision.

    Args:
        a (Decimal | None): First decimal to add.
        b (Decimal | None): Second decimal to add.
        precision (str): Quantization precision (default: "0.001" for 3 decimal places).

    Returns:
        Decimal | None: The sum of both decimals, or None if both were None.
    """
    if a is None and b is None:
        return None
    total = (a or Decimal("0")) + (b or Decimal("0"))
    return total.quantize(Decimal(precision))


def _sum_int_optional(a: int | None, b: int | None) -> int | None:
    """Add two optional integers.

    Args:
        a (int | None): First integer to add.
        b (int | None): Second integer to add.

    Returns:
        int | None: The sum of both integers, or None if both were None.
    """
    if a is None and b is None:
        return None
    return (a or 0) + (b or 0)


def _sum_list_optional(a: list[Any] | None, b: list[Any] | None) -> list[Any] | None:
    """Combine two lists, removing duplicates.

    Args:
        a (list[Any] | None): First list to combine.
        b (list[Any] | None): Second list to combine.

    Returns:
        list[Any] | None: Combined list with unique elements.
    """
    return list(set((a or []) + (b or []))) if (a or b) else None


class Sugars(BaseSchema):
    """Contains sugar information for an ingredient.

    Attributes:
        sugar_g (Decimal | None): Sugar content in grams, if available.
        added_sugars_g (Decimal | None): Added sugars content in grams, if available.
    """

    sugar_g: Decimal | None = Field(
        None,
        ge=0,
        description="Sugar content in grams",
    )
    added_sugars_g: Decimal | None = Field(
        None,
        ge=0,
        description="Added sugars in grams",
    )

    def __add__(self, other: "Sugars") -> "Sugars":
        """Combine sugar values from two entities.

        Args:
            other (Sugars): The other entity to add.

        Returns:
            Sugars: A sum of all sugar data.
        """
        return Sugars(
            sugar_g=_sum_decimal_optional(
                self.sugar_g,
                other.sugar_g,
                "0.001",  # 3 decimal places for macronutrients
            ),
            added_sugars_g=_sum_decimal_optional(
                self.added_sugars_g,
                other.added_sugars_g,
                "0.001",  # 3 decimal places for macronutrients
            ),
        )


class Fats(BaseSchema):
    """Contains fat information for an ingredient.

    Attributes:
        fat_g (Decimal | None): Total fat content in grams, if available.
        saturated_fat_g (Decimal | None): Saturated fat content in grams, if available.
        monounsaturated_fat_g (Decimal | None): Monounsaturated fat content in grams, if
            available.
        polyunsaturated_fat_g (Decimal | None): Polyunsaturated fat content in grams, if
            available.
        omega_3_fat_g (Decimal | None): Omega-3 fat content in grams, if available.
        omega_6_fat_g (Decimal | None): Omega-6 fat content in grams, if available.
        omega_9_fat_g (Decimal | None): Omega-9 fat content in grams, if available.
        trans_fat_g (Decimal | None): Trans fat content in grams, if available.
    """

    fat_g: Decimal | None = Field(
        None,
        ge=0,
        description="Fat content in grams",
    )
    saturated_fat_g: Decimal | None = Field(
        None,
        ge=0,
        description="Saturated fat content in grams",
    )
    monounsaturated_fat_g: Decimal | None = Field(
        None,
        ge=0,
        description="Monounsaturated fat content in grams",
    )
    polyunsaturated_fat_g: Decimal | None = Field(
        None,
        ge=0,
        description="Polyunsaturated fat content in grams",
    )
    omega_3_fat_g: Decimal | None = Field(
        None,
        ge=0,
        description="Omega-3 fat content in grams",
    )
    omega_6_fat_g: Decimal | None = Field(
        None,
        ge=0,
        description="Omega-6 fat content in grams",
    )
    omega_9_fat_g: Decimal | None = Field(
        None,
        ge=0,
        description="Omega-9 fat content in grams",
    )
    trans_fat_g: Decimal | None = Field(
        None,
        ge=0,
        description="Trans fat content in grams",
    )

    def __add__(self, other: "Fats") -> "Fats":
        """Combine fat values from two entities.

        Args:
            other (Fats): The other entity to add.

        Returns:
            Fats: A sum of all fat data.
        """
        return Fats(
            fat_g=_sum_decimal_optional(self.fat_g, other.fat_g, "0.001"),
            saturated_fat_g=_sum_decimal_optional(
                self.saturated_fat_g,
                other.saturated_fat_g,
                "0.001",
            ),
            monounsaturated_fat_g=_sum_decimal_optional(
                self.monounsaturated_fat_g,
                other.monounsaturated_fat_g,
                "0.001",
            ),
            polyunsaturated_fat_g=_sum_decimal_optional(
                self.polyunsaturated_fat_g,
                other.polyunsaturated_fat_g,
                "0.001",
            ),
            omega_3_fat_g=_sum_decimal_optional(
                self.omega_3_fat_g,
                other.omega_3_fat_g,
                "0.001",
            ),
            omega_6_fat_g=_sum_decimal_optional(
                self.omega_6_fat_g,
                other.omega_6_fat_g,
                "0.001",
            ),
            omega_9_fat_g=_sum_decimal_optional(
                self.omega_9_fat_g,
                other.omega_9_fat_g,
                "0.001",
            ),
            trans_fat_g=_sum_decimal_optional(
                self.trans_fat_g,
                other.trans_fat_g,
                "0.001",
            ),
        )


class Fibers(BaseSchema):
    """Contains fiber information for an ingredient.

    Attributes:
        fiber_g (Decimal | None): Total fiber content in grams, if available.
        soluble_fiber_g (Decimal | None): Soluble fiber in grams, if available.
        insoluble_fiber_g (Decimal | None): Insoluble fiber in grams, if available.
    """

    fiber_g: Decimal | None = Field(
        None,
        ge=0,
        description="Total fiber content in grams",
    )
    soluble_fiber_g: Decimal | None = Field(
        None,
        ge=0,
        description="Soluble fiber in grams",
    )
    insoluble_fiber_g: Decimal | None = Field(
        None,
        ge=0,
        description="Insoluble fiber in grams",
    )

    def __add__(self, other: "Fibers") -> "Fibers":
        """Combine fiber values from two entities.

        Args:
            other (Fibers): The other entity to add.

        Returns:
            Fibers: A sum of all fiber data.
        """
        return Fibers(
            fiber_g=_sum_decimal_optional(
                self.fiber_g,
                other.fiber_g,
                "0.001",  # 3 decimal places for macronutrients
            ),
            soluble_fiber_g=_sum_decimal_optional(
                self.soluble_fiber_g,
                other.soluble_fiber_g,
                "0.001",  # 3 decimal places for macronutrients
            ),
            insoluble_fiber_g=_sum_decimal_optional(
                self.insoluble_fiber_g,
                other.insoluble_fiber_g,
                "0.001",  # 3 decimal places for macronutrients
            ),
        )


class MacroNutrients(BaseSchema):
    """Contains macro-nutrient information for an ingredient.

    Attributes:
        calories (int | None): Total calories per serving.
        carbs_g (Decimal | None): Carbohydrate content in grams.
        cholesterol_mg (Decimal | None): Cholesterol content in milligrams, if
            available.
        protein_g (Decimal | None): Protein content in grams.
        sugars (Sugars): Sugar information.
        fats (Fats): Fat information.
        fibers (Fibers): Fiber information.
    """

    calories: int | None = Field(
        None,
        ge=0,
        description="Total calories per serving",
    )
    carbs_g: Decimal | None = Field(
        None,
        ge=0,
        description="Carbohydrate content in grams",
    )
    cholesterol_mg: Decimal | None = Field(
        None,
        ge=0,
        description="Cholesterol content in milligrams",
    )
    protein_g: Decimal | None = Field(
        None,
        ge=0,
        description="Protein content in grams",
    )
    sugars: Sugars = Field(
        default_factory=Sugars,
        description="Sugar information",
    )
    fats: Fats = Field(
        default_factory=Fats,
        description="Fat information",
    )
    fibers: Fibers = Field(
        default_factory=Fibers,
        description="Fiber information",
    )

    def __add__(self, other: "MacroNutrients") -> "MacroNutrients":
        """Combine all macro-nutrient values from two entities.

        Args:
            other (MacroNutrients): The other entity to add.

        Returns:
            MacroNutrients: A sum of all macro-nutrient data.
        """
        return MacroNutrients(
            calories=_sum_int_optional(
                self.calories,
                other.calories,
            ),
            carbs_g=_sum_decimal_optional(
                self.carbs_g,
                other.carbs_g,
                "0.001",  # 3 decimal places for macronutrients
            ),
            cholesterol_mg=_sum_decimal_optional(
                self.cholesterol_mg,
                other.cholesterol_mg,
                "0.001",  # 3 decimal places for macronutrients
            ),
            protein_g=_sum_decimal_optional(
                self.protein_g,
                other.protein_g,
                "0.001",  # 3 decimal places for macronutrients
            ),
            sugars=(self.sugars or Sugars()) + (other.sugars or Sugars()),
            fats=(self.fats or Fats()) + (other.fats or Fats()),
            fibers=(self.fibers or Fibers()) + (other.fibers or Fibers()),
        )


class Vitamins(BaseSchema):
    """Contains vitamin information for an ingredient.

    Attributes:
        vitamin_a_mg (Decimal | None): Vitamin A in milligrams, if available.
        vitamin_b6_mg (Decimal | None): Vitamin B6 in milligrams, if available.
        vitamin_b12_mg (Decimal | None): Vitamin B12 in milligrams, if available.
        vitamin_c_mg (Decimal | None): Vitamin C in milligrams, if available.
        vitamin_d_mg (Decimal | None): Vitamin D in milligrams, if available.
        vitamin_e_mg (Decimal | None): Vitamin E in milligrams, if available.
        vitamin_k_mg (Decimal | None): Vitamin K in milligrams, if available.
    """

    vitamin_a_mg: Decimal | None = Field(
        None,
        ge=0,
        description="Vitamin A in milligrams",
    )
    vitamin_b6_mg: Decimal | None = Field(
        None,
        ge=0,
        description="Vitamin B6 in milligrams",
    )
    vitamin_b12_mg: Decimal | None = Field(
        None,
        ge=0,
        description="Vitamin B12 in milligrams",
    )
    vitamin_c_mg: Decimal | None = Field(
        None,
        ge=0,
        description="Vitamin C in milligrams",
    )
    vitamin_d_mg: Decimal | None = Field(
        None,
        ge=0,
        description="Vitamin D in milligrams",
    )
    vitamin_e_mg: Decimal | None = Field(
        None,
        ge=0,
        description="Vitamin E in milligrams",
    )
    vitamin_k_mg: Decimal | None = Field(
        None,
        ge=0,
        description="Vitamin K in milligrams",
    )

    def __add__(self, other: "Vitamins") -> "Vitamins":
        """Combine all vitamin values from to entities.

        Args:
            other (Vitamins): The other entity to add.

        Returns:
            Vitamins: A sum of all vitamin data.
        """
        return Vitamins(
            vitamin_a_mg=_sum_decimal_optional(
                self.vitamin_a_mg,
                other.vitamin_a_mg,
                "0.000001",  # 6 decimal places for vitamins
            ),
            vitamin_b6_mg=_sum_decimal_optional(
                self.vitamin_b6_mg,
                other.vitamin_b6_mg,
                "0.000001",  # 6 decimal places for vitamins
            ),
            vitamin_b12_mg=_sum_decimal_optional(
                self.vitamin_b12_mg,
                other.vitamin_b12_mg,
                "0.000001",  # 6 decimal places for vitamins
            ),
            vitamin_c_mg=_sum_decimal_optional(
                self.vitamin_c_mg,
                other.vitamin_c_mg,
                "0.000001",  # 6 decimal places for vitamins
            ),
            vitamin_d_mg=_sum_decimal_optional(
                self.vitamin_d_mg,
                other.vitamin_d_mg,
                "0.000001",  # 6 decimal places for vitamins
            ),
            vitamin_e_mg=_sum_decimal_optional(
                self.vitamin_e_mg,
                other.vitamin_e_mg,
                "0.000001",  # 6 decimal places for vitamins
            ),
            vitamin_k_mg=_sum_decimal_optional(
                self.vitamin_k_mg,
                other.vitamin_k_mg,
                "0.000001",  # 6 decimal places for vitamins
            ),
        )


class Minerals(BaseSchema):
    """Contains mineral information for an ingredient.

    Attributes:
        calcium_mg (Decimal | None): Calcium in milligrams, if available.
        iron_mg (Decimal | None): Iron in milligrams, if available.
        magnesium_mg (Decimal | None): Magnesium in milligrams, if available.
        potassium_mg (Decimal | None): Potassium in milligrams, if available.
        sodium_mg (Decimal | None): Sodium in milligrams, if available.
        zinc_mg (Decimal | None): Zinc in milligrams, if available.
    """

    calcium_mg: Decimal | None = Field(
        None,
        ge=0,
        description="Calcium in milligrams",
    )
    iron_mg: Decimal | None = Field(
        None,
        ge=0,
        description="Iron in milligrams",
    )
    magnesium_mg: Decimal | None = Field(
        None,
        ge=0,
        description="Magnesium in milligrams",
    )
    potassium_mg: Decimal | None = Field(
        None,
        ge=0,
        description="Potassium in milligrams",
    )
    sodium_mg: Decimal | None = Field(
        None,
        ge=0,
        description="Sodium in milligrams",
    )
    zinc_mg: Decimal | None = Field(
        None,
        ge=0,
        description="Zinc in milligrams",
    )

    def __add__(self, other: "Minerals") -> "Minerals":
        """Combine all mineral values from to entities.

        Args:
            other (Minerals): The other entity to add.

        Returns:
            Minerals: A sum of all mineral data.
        """
        return Minerals(
            calcium_mg=_sum_decimal_optional(
                self.calcium_mg,
                other.calcium_mg,
                "0.000001",  # 6 decimal places for minerals
            ),
            iron_mg=_sum_decimal_optional(
                self.iron_mg,
                other.iron_mg,
                "0.000001",  # 6 decimal places for minerals
            ),
            magnesium_mg=_sum_decimal_optional(
                self.magnesium_mg,
                other.magnesium_mg,
                "0.000001",  # 6 decimal places for minerals
            ),
            potassium_mg=_sum_decimal_optional(
                self.potassium_mg,
                other.potassium_mg,
                "0.000001",  # 6 decimal places for minerals
            ),
            sodium_mg=_sum_decimal_optional(
                self.sodium_mg,
                other.sodium_mg,
                "0.000001",  # 6 decimal places for minerals
            ),
            zinc_mg=_sum_decimal_optional(
                self.zinc_mg,
                other.zinc_mg,
                "0.000001",  # 6 decimal places for minerals
            ),
        )


class IngredientClassification(BaseSchema):
    """Contains meta and classification information for an ingredient.

    Attributes:
        allergies (list[Allergy]): Key allergy indicators for the ingredient.
        food_groups (list[str]): Food groups this ingredient belongs to.
        nutriscore_score (int | None): Nutri-Score value for the ingredient.
        nutriscore_grade (str | None): Nutri-Score letter grade for the ingredient.
        product_name (str | None): Product name from nutritional database.
        brands (str | None): Brand information from nutritional database.
        categories (str | None): Product categories from nutritional database.
    """

    allergies: list[Allergy] | None = Field(
        None,
        description="List of allergens associated with the ingredient",
    )
    food_groups: list[str] | None = Field(
        None,
        description="Food groups this ingredient belongs to",
    )
    nutriscore_score: int | None = Field(
        None,
        ge=1,
        le=5,
        description="Nutri-Score value for the ingredient, between 1 and 5",
    )
    nutriscore_grade: str | None = Field(
        None,
        description="Nutri-Score letter grade (A-E) for the ingredient",
    )
    product_name: str | None = Field(
        None,
        description="Product name from nutritional database",
    )
    brands: str | None = Field(
        None,
        description="Brand information from nutritional database",
    )
    categories: str | None = Field(
        None,
        description="Product categories from nutritional database",
    )

    def __add__(self, other: "IngredientClassification") -> "IngredientClassification":
        """Combine classification values from two entities.

        Args:
            other (IngredientClassification): The other entity to add.

        Returns:
            IngredientClassification: A merged classification.
        """
        return IngredientClassification(
            allergies=_sum_list_optional(
                self.allergies,
                other.allergies,
            ),
            food_groups=_sum_list_optional(
                self.food_groups,
                other.food_groups,
            ),
            nutriscore_score=_sum_int_optional(
                self.nutriscore_score,
                other.nutriscore_score,
            ),
            nutriscore_grade=_combine_nutriscore_grades_optional(
                self.nutriscore_grade,
                other.nutriscore_grade,
            ),
            product_name=_combine_string_optional(
                self.product_name,
                other.product_name,
            ),
            brands=_combine_string_optional(
                self.brands,
                other.brands,
            ),
            categories=_combine_string_optional(
                self.categories,
                other.categories,
            ),
        )


class IngredientNutritionalInfoResponse(BaseSchema):
    """Contains overall nutritional information.

    Attributes:
        quantity (Quantity): Quantity of the ingredient associated with the info.
        classification (IngredientClassification): Meta and classification details.
        macro_nutrients (MacroNutrients): Macro-nutrient details.
        vitamins (Vitamins): Vitamin content details.
        minerals (Minerals): Mineral content details.
    """

    quantity: Quantity = Field(
        ...,
        description="Quantity of the ingredient associated with the nutritional info",
    )
    classification: IngredientClassification = Field(
        default_factory=IngredientClassification,
        description="Classification and meta information for the ingredient",
    )
    macro_nutrients: MacroNutrients = Field(
        default_factory=MacroNutrients,
        description="Macro-nutrient details for the ingredient",
    )
    vitamins: Vitamins = Field(
        default_factory=Vitamins,
        description="Vitamin content details for the ingredient",
    )
    minerals: Minerals = Field(
        default_factory=Minerals,
        description="Mineral content details for the ingredient",
    )

    def adjust_quantity(
        self,
        new_quantity: Quantity,
    ) -> None:
        """Adjust all nutritional values based on the new quantity.

        Scales all nutritional values proportionally based on the ratio between
        the new quantity and the current quantity, properly handling unit conversions.

        Args:
            new_quantity (Quantity): The new quantity to scale to.
        """
        if (
            not self.quantity
            or not self.quantity.quantity_value
            or not new_quantity.quantity_value
        ):
            self.quantity = new_quantity
            return

        # Get units (use UNIT as default if None)
        old_unit = (
            self.quantity.measurement
            if self.quantity.measurement
            else IngredientUnitEnum.UNIT
        )
        new_unit = (
            new_quantity.measurement
            if new_quantity.measurement
            else IngredientUnitEnum.UNIT
        )

        # Calculate scaling factor using proper unit conversion
        scale_factor = UnitConverter.calculate_scale_factor(
            old_quantity=Decimal(str(self.quantity.quantity_value)),
            old_unit=old_unit,
            new_quantity=Decimal(str(new_quantity.quantity_value)),
            new_unit=new_unit,
        )

        # Helper function to scale decimal values with appropriate precision
        def scale_macro_value(value: Decimal | None) -> Decimal | None:
            """Scale macronutrient values (3 decimal places)."""
            if value is None:
                return None
            return (value * scale_factor).quantize(Decimal("0.001"))

        def scale_micro_value(value: Decimal | None) -> Decimal | None:
            """Scale vitamin/mineral values (6 decimal places)."""
            if value is None:
                return None
            return (value * scale_factor).quantize(Decimal("0.000001"))

        # Helper function to scale integer values
        def scale_int(value: int | None) -> int | None:
            if value is None:
                return None
            return int(value * scale_factor)

        # Scale macro nutrients
        if self.macro_nutrients.calories is not None:
            self.macro_nutrients.calories = scale_int(self.macro_nutrients.calories)
        self.macro_nutrients.carbs_g = scale_macro_value(
            self.macro_nutrients.carbs_g,
        )
        self.macro_nutrients.cholesterol_mg = scale_macro_value(
            self.macro_nutrients.cholesterol_mg,
        )
        self.macro_nutrients.protein_g = scale_macro_value(
            self.macro_nutrients.protein_g,
        )

        # Scale sugars
        self.macro_nutrients.sugars.sugar_g = scale_macro_value(
            self.macro_nutrients.sugars.sugar_g,
        )
        self.macro_nutrients.sugars.added_sugars_g = scale_macro_value(
            self.macro_nutrients.sugars.added_sugars_g,
        )

        # Scale fats
        self.macro_nutrients.fats.fat_g = scale_macro_value(
            self.macro_nutrients.fats.fat_g,
        )
        self.macro_nutrients.fats.saturated_fat_g = scale_macro_value(
            self.macro_nutrients.fats.saturated_fat_g,
        )
        self.macro_nutrients.fats.monounsaturated_fat_g = scale_macro_value(
            self.macro_nutrients.fats.monounsaturated_fat_g,
        )
        self.macro_nutrients.fats.polyunsaturated_fat_g = scale_macro_value(
            self.macro_nutrients.fats.polyunsaturated_fat_g,
        )
        self.macro_nutrients.fats.omega_3_fat_g = scale_macro_value(
            self.macro_nutrients.fats.omega_3_fat_g,
        )
        self.macro_nutrients.fats.omega_6_fat_g = scale_macro_value(
            self.macro_nutrients.fats.omega_6_fat_g,
        )
        self.macro_nutrients.fats.omega_9_fat_g = scale_macro_value(
            self.macro_nutrients.fats.omega_9_fat_g,
        )
        self.macro_nutrients.fats.trans_fat_g = scale_macro_value(
            self.macro_nutrients.fats.trans_fat_g,
        )

        # Scale fibers
        self.macro_nutrients.fibers.fiber_g = scale_macro_value(
            self.macro_nutrients.fibers.fiber_g,
        )
        self.macro_nutrients.fibers.soluble_fiber_g = scale_macro_value(
            self.macro_nutrients.fibers.soluble_fiber_g,
        )
        self.macro_nutrients.fibers.insoluble_fiber_g = scale_macro_value(
            self.macro_nutrients.fibers.insoluble_fiber_g,
        )

        # Scale vitamins (6 decimal places precision)
        self.vitamins.vitamin_a_mg = scale_micro_value(self.vitamins.vitamin_a_mg)
        self.vitamins.vitamin_b6_mg = scale_micro_value(self.vitamins.vitamin_b6_mg)
        self.vitamins.vitamin_b12_mg = scale_micro_value(self.vitamins.vitamin_b12_mg)
        self.vitamins.vitamin_c_mg = scale_micro_value(self.vitamins.vitamin_c_mg)
        self.vitamins.vitamin_d_mg = scale_micro_value(self.vitamins.vitamin_d_mg)
        self.vitamins.vitamin_e_mg = scale_micro_value(self.vitamins.vitamin_e_mg)
        self.vitamins.vitamin_k_mg = scale_micro_value(self.vitamins.vitamin_k_mg)

        # Scale minerals (6 decimal places precision)
        self.minerals.calcium_mg = scale_micro_value(self.minerals.calcium_mg)
        self.minerals.iron_mg = scale_micro_value(self.minerals.iron_mg)
        self.minerals.magnesium_mg = scale_micro_value(self.minerals.magnesium_mg)
        self.minerals.potassium_mg = scale_micro_value(self.minerals.potassium_mg)
        self.minerals.sodium_mg = scale_micro_value(self.minerals.sodium_mg)
        self.minerals.zinc_mg = scale_micro_value(self.minerals.zinc_mg)

        # Update quantity last
        self.quantity = new_quantity

    def __add__(
        self,
        other: "IngredientNutritionalInfoResponse",
    ) -> "IngredientNutritionalInfoResponse":
        """Combine all nutritional values from two entities.

        Args:
            other (IngredientNutritionalInfoResponse): The other entity to add.

        Returns:
            IngredientNutritionalInfoResponse: A sum of all nutritional data.
        """
        return IngredientNutritionalInfoResponse(
            quantity=self.quantity,  # Keep the first entity's quantity
            classification=self.classification + other.classification,
            macro_nutrients=self.macro_nutrients + other.macro_nutrients,
            vitamins=self.vitamins + other.vitamins,
            minerals=self.minerals + other.minerals,
        )

    @classmethod
    def calculate_total_nutritional_info(
        cls,
        ingredients: list["IngredientNutritionalInfoResponse"],
    ) -> "IngredientNutritionalInfoResponse":
        """Calculate total nutritional information from a list of ingredients.

        Args:
            ingredients (list[IngredientNutritionalInfoResponse]): List of ingredient
                nutritional info responses.

        Returns:
            IngredientNutritionalInfoResponse: Total nutritional info response.
        """
        if not ingredients:
            return IngredientNutritionalInfoResponse(
                quantity=Quantity(
                    quantity_value=Decimal("0"),
                    measurement=IngredientUnitEnum.UNIT,
                ),
            )

        total = IngredientNutritionalInfoResponse(
            quantity=Quantity(
                quantity_value=Decimal("0"),
                measurement=IngredientUnitEnum.UNIT,
            ),
        )
        nutriscores = [
            ing.classification.nutriscore_score
            for ing in ingredients
            if ing.classification.nutriscore_score is not None
        ]
        for ingredient in ingredients:
            total += ingredient

        # Average nutriscore if any present
        if nutriscores:
            avg_nutriscore = round(sum(nutriscores) / len(nutriscores))
            total.classification.nutriscore_score = avg_nutriscore
        else:
            total.classification.nutriscore_score = None

        return total

    @classmethod
    def from_db_model(
        cls,
        nutritional_info: "NutritionalInfo",
    ) -> "IngredientNutritionalInfoResponse":
        """Create an instance from a NutritionalInfo database model.

        Args:
            nutritional_info (NutritionalInfo): The database model to convert.

        Returns:
            IngredientNutritionalInfoResponse: The converted response schema.
        """
        return cls(
            quantity=Quantity(
                quantity_value=nutritional_info.serving_quantity,
                measurement=(
                    nutritional_info.serving_measurement
                    if nutritional_info.serving_measurement is not None
                    else IngredientUnitEnum.UNIT
                ),
            ),
            classification=IngredientClassification(
                allergies=nutritional_info.allergens or [],
                food_groups=(
                    [nutritional_info.food_groups]
                    if nutritional_info.food_groups
                    else []
                ),
                nutriscore_score=nutritional_info.nutriscore_score,
                nutriscore_grade=nutritional_info.nutriscore_grade,
                product_name=nutritional_info.product_name,
                brands=nutritional_info.brands,
                categories=nutritional_info.categories,
            ),
            macro_nutrients=MacroNutrients(
                calories=(
                    int(nutritional_info.energy_kcal_100g)
                    if nutritional_info.energy_kcal_100g
                    else None
                ),
                carbs_g=nutritional_info.carbohydrates_100g,
                cholesterol_mg=nutritional_info.cholesterol_100g,
                protein_g=nutritional_info.proteins_100g,
                sugars=Sugars(
                    sugar_g=nutritional_info.sugars_100g,
                    added_sugars_g=nutritional_info.added_sugars_100g,
                ),
                fats=Fats(
                    fat_g=nutritional_info.fat_100g,
                    saturated_fat_g=nutritional_info.saturated_fat_100g,
                    monounsaturated_fat_g=nutritional_info.monounsaturated_fat_100g,
                    polyunsaturated_fat_g=nutritional_info.polyunsaturated_fat_100g,
                    omega_3_fat_g=nutritional_info.omega_3_fat_100g,
                    omega_6_fat_g=nutritional_info.omega_6_fat_100g,
                    omega_9_fat_g=nutritional_info.omega_9_fat_100g,
                    trans_fat_g=nutritional_info.trans_fat_100g,
                ),
                fibers=Fibers(
                    fiber_g=nutritional_info.fiber_100g,
                    soluble_fiber_g=nutritional_info.soluble_fiber_100g,
                    insoluble_fiber_g=nutritional_info.insoluble_fiber_100g,
                ),
            ),
            vitamins=Vitamins(
                vitamin_a_mg=nutritional_info.vitamin_a_100g,
                vitamin_b6_mg=nutritional_info.vitamin_b6_100g,
                vitamin_b12_mg=nutritional_info.vitamin_b12_100g,
                vitamin_c_mg=nutritional_info.vitamin_c_100g,
                vitamin_d_mg=nutritional_info.vitamin_d_100g,
                vitamin_e_mg=nutritional_info.vitamin_e_100g,
                vitamin_k_mg=nutritional_info.vitamin_k_100g,
            ),
            minerals=Minerals(
                calcium_mg=nutritional_info.calcium_100g,
                iron_mg=nutritional_info.iron_100g,
                magnesium_mg=nutritional_info.magnesium_100g,
                potassium_mg=nutritional_info.potassium_100g,
                sodium_mg=nutritional_info.sodium_100g,
                zinc_mg=nutritional_info.zinc_100g,
            ),
        )
