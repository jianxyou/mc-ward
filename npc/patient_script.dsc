# --- Burn Patient --- 
patient_one_assignment:
    type: assignment
    actions:
        on assignment:
        - trigger name:chat state:true radius:2
    interact scripts:
    - patient_one_interact

patient_one_interact:
    type: interact
    steps:
        1:
            chat trigger:
                1:
                    trigger: /regex:^(?i)\b(hello|hi|good morning|good afternoon|good evening|hey |how are you)\b/ patient one!
                    script:
                    - chat "Hello Doctor, I'm burning"
                    - chat "Do you have something ?"
                2:
                    trigger: /regex:^(?i)\b(this is for you|I got it|I got you|this in on me|I put it on the chest|Bye|Goodbye|This potion is for you)\b/
                    script:
                    - chat "Thank you!"
                    - chat "See you later Doctor!"


# --- Senior Patient --- 
patient_two_assignment:
    type: assignment
    actions:
        on assignment:
        - trigger name:chat state:true radius:2
    interact scripts:
    - patient_two_interact

patient_two_interact:
    type: interact
    steps:
        1:
            chat trigger:
                1:
                    trigger: /regex:^(?i)\b(hello|hi|good morning|good afternoon|good evening|hey |how are you)\b/ patient two!
                    script:
                    - chat "Hello Doctor, I fell again."
                    - chat "Give me something!"
                2:
                    trigger: /regex:^(?i)\b(this is for you|I got it|I got you|this in on me|I put it on the chest|Bye|Goodbye|This potion is for you)\b/
                    script:
                    - chat "Thank you young folk!"
                    - chat "Goodbye"


# --- Accident Patient ---
patient_three_assignment:
    type: assignment
    actions:
        on assignment:
        - trigger name:chat state:true radius:2
    interact scripts:
    - patient_three_interact

patient_three_interact:
    type: interact
    steps:
        1:
            chat trigger:
                1:
                    trigger: /regex:^(?i)\b(hello|hi|good morning|good afternoon|good evening|hey |how are you)\b/ patient three!
                    script:
                    - chat "Hi Doctor, I'm feeling dizzy"
                    - chat "Am I still alive ?"
                2:
                    trigger: /regex:^(?i)\b(this is for you|I got it|I got you|this in on me|I put it on the chest|Bye|Goodbye|This potion is for you)\b/
                    script:
                    - chat "Thanks."
                    - chat "Bye..."

                    
# --- Sick Patient ---
patient_four_assignment:
    type: assignment
    actions:
        on assignment:
        - trigger name:chat state:true radius:2
    interact scripts:
    - patient_four_interact

patient_four_interact:
    type: interact
    steps:
        1:
            chat trigger:
                1:
                    trigger: /regex:^(?i)\b(hello|hi|good morning|good afternoon|good evening|hey |how are you)\b/ patient four!
                    script:
                    - chat "Good morning Doctor, I'm quite sick"
                    - chat "#Cough# Give me some medecine"
                2:
                    trigger: /regex:^(?i)\b(this is for you|I got it|I got you|this in on me|I put it on the chest|Bye|Goodbye|This potion is for you)\b/
                    script:
                    - chat "#Cough Cough# Bye doctor!"