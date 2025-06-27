"""Contains common schema definitions for nutritional information."""

from decimal import Decimal
from typing import TYPE_CHECKING

from pydantic import Field

from app.api.v1.schemas.base_schema import BaseSchema
from app.api.v1.schemas.common.ingredient import Quantity
from app.api.v1.schemas.common.nutritional_info.fats import Fats
from app.api.v1.schemas.common.nutritional_info.fibers import Fibers
from app.api.v1.schemas.common.nutritional_info.ingredient_classification import (
    IngredientClassification,
)
from app.api.v1.schemas.common.nutritional_info.macro_nutrients import MacroNutrients
from app.api.v1.schemas.common.nutritional_info.minerals import Minerals
from app.api.v1.schemas.common.nutritional_info.sugars import Sugars
from app.api.v1.schemas.common.nutritional_info.vitams import Vitamins
from app.enums.ingredient_unit_enum import IngredientUnitEnum
from app.utils.unit_converter import UnitConverter

if TYPE_CHECKING:
    from app.db.models.nutritional_info_models.nutritional_info import NutritionalInfo


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
        if not self.quantity or not self.quantity.amount or not new_quantity.amount:
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
            old_quantity=Decimal(str(self.quantity.amount)),
            old_unit=old_unit,
            new_quantity=Decimal(str(new_quantity.amount)),
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
                    amount=Decimal("0"),
                    measurement=IngredientUnitEnum.UNIT,
                ),
            )

        total = IngredientNutritionalInfoResponse(
            quantity=Quantity(
                amount=Decimal("0"),
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
                amount=nutritional_info.serving_quantity,
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
                    else None
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
