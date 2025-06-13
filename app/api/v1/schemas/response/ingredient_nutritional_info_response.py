"""Contains common schema definitions for nutritional information."""

from typing import Any

from pydantic import Field

from app.api.v1.schemas.base_schema import BaseSchema
from app.enums.allergy import Allergy


def _sum_float_optional(a: float | None, b: float | None) -> float | None:
    """Add two optional floats & rounds to 2 decimal points.

    Args:
        a (float | None): First float to add.
        b (float | None): Second float to add.

    Returns:
        float | None: The sum of both floats, or None if both were None.
    """
    if a is None and b is None:
        return None
    total = (a or 0.0) + (b or 0.0)
    return round(total, 2)


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
        sugar_g (float | None): Sugar content in grams, if available.
        added_sugars_g (float | None): Added sugars content in grams, if available.
    """

    sugar_g: float | None = Field(
        None,
        ge=0,
        description="Sugar content in grams",
    )
    added_sugars_g: float | None = Field(
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
            sugar_g=_sum_float_optional(
                self.sugar_g,
                other.sugar_g,
            ),
            added_sugars_g=_sum_float_optional(
                self.added_sugars_g,
                other.added_sugars_g,
            ),
        )


class Fats(BaseSchema):
    """Contains fat information for an ingredient.

    Attributes:
        fat_g (float | None): Total fat content in grams, if available.
        saturated_fat_g (float | None): Saturated fat content in grams, if available.
        monounsaturated_fat_g (float | None): Monounsaturated fat content in grams, if
            available.
        polyunsaturated_fat_g (float | None): Polyunsaturated fat content in grams, if
            available.
        omega_3_fat_g (float | None): Omega-3 fat content in grams, if available.
        omega_6_fat_g (float | None): Omega-6 fat content in grams, if available.
        trans_fat_g (float | None): Trans fat content in grams, if available.
    """

    fat_g: float | None = Field(
        None,
        ge=0,
        description="Fat content in grams",
    )
    saturated_fat_g: float | None = Field(
        None,
        ge=0,
        description="Saturated fat content in grams",
    )
    monounsaturated_fat_g: float | None = Field(
        None,
        ge=0,
        description="Monounsaturated fat content in grams",
    )
    polyunsaturated_fat_g: float | None = Field(
        None,
        ge=0,
        description="Polyunsaturated fat content in grams",
    )
    omega_3_fat_g: float | None = Field(
        None,
        ge=0,
        description="Omega-3 fat content in grams",
    )
    omega_6_fat_g: float | None = Field(
        None,
        ge=0,
        description="Omega-6 fat content in grams",
    )
    trans_fat_g: float | None = Field(
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
            fat_g=_sum_float_optional(self.fat_g, other.fat_g),
            saturated_fat_g=_sum_float_optional(
                self.saturated_fat_g,
                other.saturated_fat_g,
            ),
            monounsaturated_fat_g=_sum_float_optional(
                self.monounsaturated_fat_g,
                other.monounsaturated_fat_g,
            ),
            polyunsaturated_fat_g=_sum_float_optional(
                self.polyunsaturated_fat_g,
                other.polyunsaturated_fat_g,
            ),
            omega_3_fat_g=_sum_float_optional(
                self.omega_3_fat_g,
                other.omega_3_fat_g,
            ),
            omega_6_fat_g=_sum_float_optional(
                self.omega_6_fat_g,
                other.omega_6_fat_g,
            ),
            trans_fat_g=_sum_float_optional(
                self.trans_fat_g,
                other.trans_fat_g,
            ),
        )


class Fibers(BaseSchema):
    """Contains fiber information for an ingredient.

    Attributes:
        fiber_g (float | None): Total fiber content in grams, if available.
        soluble_fiber_g (float | None): Soluble fiber in grams, if available.
        insoluble_fiber_g (float | None): Insoluble fiber in grams, if available.
    """

    fiber_g: float | None = Field(
        None,
        ge=0,
        description="Total fiber content in grams",
    )
    soluble_fiber_g: float | None = Field(
        None,
        ge=0,
        description="Soluble fiber in grams",
    )
    insoluble_fiber_g: float | None = Field(
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
            fiber_g=_sum_float_optional(
                self.fiber_g,
                other.fiber_g,
            ),
            soluble_fiber_g=_sum_float_optional(
                self.soluble_fiber_g,
                other.soluble_fiber_g,
            ),
            insoluble_fiber_g=_sum_float_optional(
                self.insoluble_fiber_g,
                other.insoluble_fiber_g,
            ),
        )


class MacroNutrients(BaseSchema):
    """Contains macro-nutrient information for an ingredient.

    Attributes:
        calories (float): Total calories per serving.
        carbs_g (float): Carbohydrate content in grams.
        cholesterol_mg (float | None): Cholesterol content in milligrams, if available.
        protein_g (float): Protein content in grams.
        sugars (Sugars): Sugar information.
        fats (Fats): Fat information.
        fibers (Fibers): Fiber information.
    """

    calories: int | None = Field(
        None,
        ge=0,
        description="Total calories per serving",
    )
    carbs_g: float | None = Field(
        None,
        ge=0,
        description="Carbohydrate content in grams",
    )
    cholesterol_mg: float | None = Field(
        None,
        ge=0,
        description="Cholesterol content in milligrams",
    )
    protein_g: float | None = Field(
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
            carbs_g=_sum_float_optional(
                self.carbs_g,
                other.carbs_g,
            ),
            cholesterol_mg=_sum_float_optional(
                self.cholesterol_mg,
                other.cholesterol_mg,
            ),
            protein_g=_sum_float_optional(
                self.protein_g,
                other.protein_g,
            ),
            sugars=(self.sugars or Sugars()) + (other.sugars or Sugars()),
            fats=(self.fats or Fats()) + (other.fats or Fats()),
            fibers=(self.fibers or Fibers()) + (other.fibers or Fibers()),
        )


class Vitamins(BaseSchema):
    """Contains vitamin information for an ingredient.

    Attributes:
        vitamin_a_mcg (float | None): Vitamin A in micrograms, if available.
        vitamin_b6_mg (float | None): Vitamin B6 in milligrams, if available.
        vitamin_b12_mcg (float | None): Vitamin B12 in micrograms, if available.
        vitamin_c_mg (float | None): Vitamin C in milligrams, if available.
        vitamin_d_mcg (float | None): Vitamin D in micrograms, if available.
        vitamin_e_mg (float | None): Vitamin E in milligrams, if available.
        vitamin_k_mcg (float | None): Vitamin K in micrograms, if available.
    """

    vitamin_a_mcg: float | None = Field(
        None,
        ge=0,
        description="Vitamin A in micrograms",
    )
    vitamin_b6_mg: float | None = Field(
        None,
        ge=0,
        description="Vitamin B6 in milligrams",
    )
    vitamin_b12_mcg: float | None = Field(
        None,
        ge=0,
        description="Vitamin B12 in micrograms",
    )
    vitamin_c_mg: float | None = Field(
        None,
        ge=0,
        description="Vitamin C in milligrams",
    )
    vitamin_d_mcg: float | None = Field(
        None,
        ge=0,
        description="Vitamin D in micrograms",
    )
    vitamin_e_mg: float | None = Field(
        None,
        ge=0,
        description="Vitamin E in milligrams",
    )
    vitamin_k_mcg: float | None = Field(
        None,
        ge=0,
        description="Vitamin K in micrograms",
    )

    def __add__(self, other: "Vitamins") -> "Vitamins":
        """Combine all vitamin values from to entities.

        Args:
            other (Vitamins): The other entity to add.

        Returns:
            Vitamins: A sum of all vitamin data.
        """
        return Vitamins(
            vitamin_a_mcg=_sum_float_optional(
                self.vitamin_a_mcg,
                other.vitamin_a_mcg,
            ),
            vitamin_b6_mg=_sum_float_optional(
                self.vitamin_b6_mg,
                other.vitamin_b6_mg,
            ),
            vitamin_b12_mcg=_sum_float_optional(
                self.vitamin_b12_mcg,
                other.vitamin_b12_mcg,
            ),
            vitamin_c_mg=_sum_float_optional(
                self.vitamin_c_mg,
                other.vitamin_c_mg,
            ),
            vitamin_d_mcg=_sum_float_optional(
                self.vitamin_d_mcg,
                other.vitamin_d_mcg,
            ),
            vitamin_e_mg=_sum_float_optional(
                self.vitamin_e_mg,
                other.vitamin_e_mg,
            ),
            vitamin_k_mcg=_sum_float_optional(
                self.vitamin_k_mcg,
                other.vitamin_k_mcg,
            ),
        )


class Minerals(BaseSchema):
    """Contains mineral information for an ingredient.

    Attributes:
        calcium_mg (float | None): Calcium in milligrams, if available.
        iron_mg (float | None): Iron in milligrams, if available.
        magnesium_mg (float | None): Magnesium in milligrams, if available.
        potassium_mg (float | None): Potassium in milligrams, if available.
        sodium_mg (float | None): Sodium in milligrams, if available.
        zinc_mg (float | None): Zinc in milligrams, if available.
    """

    calcium_mg: float | None = Field(
        None,
        ge=0,
        description="Calcium in milligrams",
    )
    iron_mg: float | None = Field(
        None,
        ge=0,
        description="Iron in milligrams",
    )
    magnesium_mg: float | None = Field(
        None,
        ge=0,
        description="Magnesium in milligrams",
    )
    potassium_mg: float | None = Field(
        None,
        ge=0,
        description="Potassium in milligrams",
    )
    sodium_mg: float | None = Field(
        None,
        ge=0,
        description="Sodium in milligrams",
    )
    zinc_mg: float | None = Field(
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
            calcium_mg=_sum_float_optional(
                self.calcium_mg,
                other.calcium_mg,
            ),
            iron_mg=_sum_float_optional(
                self.iron_mg,
                other.iron_mg,
            ),
            magnesium_mg=_sum_float_optional(
                self.magnesium_mg,
                other.magnesium_mg,
            ),
            potassium_mg=_sum_float_optional(
                self.potassium_mg,
                other.potassium_mg,
            ),
            sodium_mg=_sum_float_optional(
                self.sodium_mg,
                other.sodium_mg,
            ),
            zinc_mg=_sum_float_optional(
                self.zinc_mg,
                other.zinc_mg,
            ),
        )


class IngredientClassification(BaseSchema):
    """Contains meta and classification information for an ingredient.

    Attributes:
        allergies (list[Allergy]): Key allergy indicators for the ingredient.
        food_groups (list[str]): Food groups this ingredient belongs to.
        nutriscore_score (int | None): Nutri-Score value for the ingredient.
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
        )


class IngredientNutritionalInfoResponse(BaseSchema):
    """Contains overall nutritional information.

    Attributes:
        classification (IngredientClassification): Meta and classification details.
        macro_nutrients (MacroNutrients): Macro-nutrient details.
        vitamins (Vitamins): Vitamin content details.
        minerals (Minerals): Mineral content details.
    """

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
            return IngredientNutritionalInfoResponse()

        total = IngredientNutritionalInfoResponse()
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
