"""Contains common schema definitions for nutritional information."""

from enum import Enum

from pydantic import BaseModel, Field


def __sum_optional(a: float | None, b: float | None) -> float | None:
    if a is None and b is None:
        return None
    return (a or 0) + (b or 0)


class Macronutrients(BaseModel):
    """Contains macro-nutrient information for an ingredient.

    Attributes:
        calories (float): Total calories per serving.
        protein_g (float): Protein content in grams.
        fat_g (float): Total fat content in grams.
        carbs_g (float): Carbohydrate content in grams.
        saturated_fat_g (float | None): Saturated fat content in grams, if available.
        monounsaturated_fat_g (float | None): Monounsaturated fat content in grams, if
            available.
        polyunsaturated_fat_g (float | None): Polyunsaturated fat content in grams, if
            available.
        trans_fat_g (float | None): Trans fat content in grams, if available.
        cholesterol_mg (float | None): Cholesterol content in milligrams, if available.
        fiber_g (float | None): Fiber content in grams, if available.
        sugar_g (float | None): Sugar content in grams, if available.
    """

    calories: float | None = Field(None, description="Total calories per serving")
    protein_g: float | None = Field(None, description="Protein content in grams")
    fat_g: float | None = Field(None, description="Fat content in grams")
    carbs_g: float | None = Field(None, description="Carbohydrate content in grams")
    saturated_fat_g: float | None = Field(
        None,
        description="Saturated fat content in grams",
    )
    monounsaturated_fat_g: float | None = Field(
        None,
        description="Monounsaturated fat content in grams",
    )
    polyunsaturated_fat_g: float | None = Field(
        None,
        description="Polyunsaturated fat content in grams",
    )
    trans_fat_g: float | None = Field(None, description="Trans fat content in grams")
    cholesterol_mg: float | None = Field(
        None,
        description="Cholesterol content in milligrams",
    )
    fiber_g: float | None = Field(None, description="Fiber content in grams")
    sugar_g: float | None = Field(None, description="Sugar content in grams")

    def __add__(self, other: "Macronutrients") -> "Macronutrients":
        """Combine all macro-nutrient values from to entities.

        Args:
            other (Macronutrients): The other entity to add.

        Returns:
            Macronutrients: A sum of all macro-nutrient data.
        """
        return Macronutrients(
            calories=__sum_optional(self.calories, other.calories),
            protein_g=__sum_optional(self.protein_g, other.protein_g),
            fat_g=__sum_optional(self.fat_g, other.fat_g),
            carbs_g=__sum_optional(self.carbs_g, other.carbs_g),
            saturated_fat_g=__sum_optional(
                self.saturated_fat_g,
                other.saturated_fat_g,
            ),
            monounsaturated_fat_g=__sum_optional(
                self.monounsaturated_fat_g,
                other.monounsaturated_fat_g,
            ),
            polyunsaturated_fat_g=__sum_optional(
                self.polyunsaturated_fat_g,
                other.polyunsaturated_fat_g,
            ),
            trans_fat_g=__sum_optional(self.trans_fat_g, other.trans_fat_g),
            cholesterol_mg=__sum_optional(
                self.cholesterol_mg,
                other.cholesterol_mg,
            ),
            fiber_g=__sum_optional(self.fiber_g, other.fiber_g),
            sugar_g=__sum_optional(self.sugar_g, other.sugar_g),
        )


class Vitamins(BaseModel):
    """Contains vitamin information for an ingredient.

    Attributes:
        vitamin_a_mcg (float | None): Vitamin A in micrograms, if available.
        vitamin_c_mg (float | None): Vitamin C in milligrams, if available.
        vitamin_d_mcg (float | None): Vitamin D in micrograms, if available.
        vitamin_k_mcg (float | None): Vitamin K in micrograms, if available.
        vitamin_b6_mg (float | None): Vitamin B6 in milligrams, if available.
        vitamin_b12_mcg (float | None): Vitamin B12 in micrograms, if available.
    """

    vitamin_a_mcg: float | None = Field(None, description="Vitamin A in micrograms")
    vitamin_c_mg: float | None = Field(None, description="Vitamin C in milligrams")
    vitamin_d_mcg: float | None = Field(None, description="Vitamin D in micrograms")
    vitamin_k_mcg: float | None = Field(None, description="Vitamin K in micrograms")
    vitamin_b6_mg: float | None = Field(None, description="Vitamin B6 in milligrams")
    vitamin_b12_mcg: float | None = Field(
        None,
        description="Vitamin B12 in micrograms",
    )

    def __add__(self, other: "Vitamins") -> "Vitamins":
        """Combine all vitamin values from to entities.

        Args:
            other (Vitamins): The other entity to add.

        Returns:
            Vitamins: A sum of all vitamin data.
        """
        return Vitamins(
            vitamin_a_mcg=__sum_optional(self.vitamin_a_mcg, other.vitamin_a_mcg),
            vitamin_c_mg=__sum_optional(self.vitamin_c_mg, other.vitamin_c_mg),
            vitamin_d_mcg=__sum_optional(self.vitamin_d_mcg, other.vitamin_d_mcg),
            vitamin_k_mcg=__sum_optional(self.vitamin_k_mcg, other.vitamin_k_mcg),
            vitamin_b6_mg=__sum_optional(self.vitamin_b6_mg, other.vitamin_b6_mg),
            vitamin_b12_mcg=__sum_optional(self.vitamin_b12_mcg, other.vitamin_b12_mcg),
        )


class Minerals(BaseModel):
    """Contains mineral information for an ingredient.

    Attributes:
        calcium_mg (float | None): Calcium in milligrams, if available.
        iron_mg (float | None): Iron in milligrams, if available.
        magnesium_mg (float | None): Magnesium in milligrams, if available.
        potassium_mg (float | None): Potassium in milligrams, if available.
        sodium_mg (float | None): Sodium in milligrams, if available.
        zinc_mg (float | None): Zinc in milligrams, if available.
    """

    calcium_mg: float | None = Field(None, description="Calcium in milligrams")
    iron_mg: float | None = Field(None, description="Iron in milligrams")
    magnesium_mg: float | None = Field(None, description="Magnesium in milligrams")
    potassium_mg: float | None = Field(None, description="Potassium in milligrams")
    sodium_mg: float | None = Field(None, description="Sodium in milligrams")
    zinc_mg: float | None = Field(None, description="Zinc in milligrams")

    def __add__(self, other: "Minerals") -> "Minerals":
        """Combine all mineral values from to entities.

        Args:
            other (Minerals): The other entity to add.

        Returns:
            Minerals: A sum of all mineral data.
        """
        return Minerals(
            calcium_mg=__sum_optional(self.calcium_mg, other.calcium_mg),
            iron_mg=__sum_optional(self.iron_mg, other.iron_mg),
            magnesium_mg=__sum_optional(self.magnesium_mg, other.magnesium_mg),
            potassium_mg=__sum_optional(self.potassium_mg, other.potassium_mg),
            sodium_mg=__sum_optional(self.sodium_mg, other.sodium_mg),
            zinc_mg=__sum_optional(self.zinc_mg, other.zinc_mg),
        )


class Allergy(str, Enum):
    """Enumeration of common allergens.

    Attributes:
        GLUTEN (str): Contains gluten.
        PEANUTS (str): Contains peanuts.
        TREE_NUTS (str): Contains tree nuts.
        DAIRY (str): Contains dairy.
        SOY (str): Contains soy.
        EGG (str): Contains egg.
        FISH (str): Contains fish.
        SHELLFISH (str): Contains shellfish.
        SESAME (str): Contains sesame.
        MUSTARD (str): Contains mustard.
        SULFITES (str): Contains sulfites.
    """

    GLUTEN = "gluten"
    PEANUTS = "peanuts"
    TREE_NUTS = "tree_nuts"
    DAIRY = "dairy"
    SOY = "soy"
    EGG = "egg"
    FISH = "fish"
    SHELLFISH = "shellfish"
    SESAME = "sesame"
    MUSTARD = "mustard"
    SULFITES = "sulfites"


class NutritionalInfo(BaseModel):
    """Contains overall nutritional information.

    Args:
        macronutrients (Macronutrients): Macro-nutrient details.
        vitamins (Vitamins): Vitamin content details.
        minerals (Minerals): Mineral content details.
        allergies (list[Allergy]): Key allergy indicators for the ingredient.
    """

    macronutrients: Macronutrients = Macronutrients()
    vitamins: Vitamins = Vitamins()
    minerals: Minerals = Minerals()
    allergies: list[Allergy] = Field(
        default_factory=list,
        description="List of allergens associated with the ingredient",
    )

    def __add__(self, other: "NutritionalInfo") -> "NutritionalInfo":
        """Combine all vitamin values from to entities.

        Args:
            other (Vitamins): The other entity to add.

        Returns:
            Vitamins: A sum of all vitamin data.
        """
        return NutritionalInfo(
            macronutrients=self.macronutrients + other.macronutrients,
            vitamins=self.vitamins + other.vitamins,
            minerals=self.minerals + other.minerals,
            allergies=list(set(self.allergies + other.allergies)),  # Avoid duplicates
        )
