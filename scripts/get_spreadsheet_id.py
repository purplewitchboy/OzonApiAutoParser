#!/usr/bin/env python3
import os
import sys
import json

def extract_id_from_url(url: str) -> str:
    """Извлечь ID из URL Google Sheets"""
    if '/spreadsheets/d/' in url:
        parts = url.split('/spreadsheets/d/')
        if len(parts) > 1:
            return parts[1].split('/')[0]
    return url

def main():
    print("=" * 60)
    print("📊 ПОЛУЧЕНИЕ ID ТАБЛИЦЫ GOOGLE SHEETS")
    print("=" * 60)
    print("\nСпособы получить ID таблицы:")
    print("1. Из URL: https://docs.google.com/spreadsheets/d/ВАШ_ID/edit")
    print("2. В Google Sheets: Файл → О таблице → Смотреть ID документа")
    print("3. Если вы не владелец, попросите владельца отправить ID")
    print("\nПример ID: 1A2B3C4D5E6F7G8H9I0J или abc123-def456-ghi789")
    
    while True:
        print("\n" + "-" * 60)
        user_input = input("\nВведите URL или ID таблицы: ").strip()
        
        if not user_input:
            print("❌ Введите что-нибудь")
            continue
        
        spreadsheet_id = extract_id_from_url(user_input)
        
        print(f"\n🔍 Извлеченный ID: {spreadsheet_id}")
        
        # Проверяем длину (примерная проверка)
        if len(spreadsheet_id) < 10:
            print("⚠️  ID кажется слишком коротким")
        else:
            print("✅ ID выглядит корректно")
        
        print(f"\n📋 Ваш ID для использования в скриптах:")
        print(f"   --spreadsheet-id {spreadsheet_id}")
        
        again = input("\nПроверить еще одну таблицу? (y/n): ").lower()
        if again != 'y':
            break
    
    print("\n🎉 Готово! Используйте этот ID в командах.")

if __name__ == "__main__":
    main()