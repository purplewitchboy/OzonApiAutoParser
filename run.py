#!/usr/bin/env python3
import sys
import os

def main():
    """Точка входа для всех команд"""
    if len(sys.argv) < 2:
        print("Использование:")
        print("  python run.py products <spreadsheet_id>   - Загрузить товары")
        print("  python run.py prices <spreadsheet_id>     - Загрузить цены")
        print("  python run.py ads <spreadsheet_id>        - Загрузить рекламную статистику")
        print("  python run.py details <spreadsheet_id>    - Загрузить детализацию транзакций")
        print("  python run.py sales-fbo <spreadsheet_id>  - Загрузить продажи FBO")
        print("  python run.py orders-fbo <spreadsheet_id> - Загрузить заказы FBO")
        print("  python run.py stock-fbo <spreadsheet_id>  - Загрузить остатки FBO")
        print("  python run.py orders-fbs <spreadsheet_id> - Загрузить заказы FBS")
        print("  python run.py stock-fbs <spreadsheet_id>  - Загрузить остатки FBS")
        print("  python run.py button - Запустить сервер для кнопки")
        print("  python run.py get-id - Получить ID таблицы")
        print("")
        print("Дополнительные опции:")
        print("  --overwrite - Перезаписать данные (для prices)")
        print("  --log-level DEBUG|INFO|WARNING|ERROR")
        print("")
        print("Примеры:")
        print("  python run.py products 1A2B3C4D5E6F7G8H9I0J")
        print("  python run.py prices 1A2B3C4D5E6F7G8H9I0J --overwrite")
        print("  python run.py ads 1A2B3C4D5E6F7G8H9I0J")
        print("  python run.py stock-fbo 1A2B3C4D5E6F7G8H9I0J")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "products":
        if len(sys.argv) < 3:
            print("Укажите ID таблицы: python run.py products <spreadsheet_id>")
            sys.exit(1)
        
        # Создаем аргументы для скрипта
        import scripts.run_products_report as products_script
        
        # Парсим дополнительные аргументы
        script_args = ['run_products_report.py', '--spreadsheet-id', sys.argv[2]]
        
        # Добавляем дополнительные аргументы если есть
        for i in range(3, len(sys.argv)):
            script_args.append(sys.argv[i])
        
        # Сохраняем оригинальные аргументы
        original_argv = sys.argv
        sys.argv = script_args
        
        try:
            products_script.main()
        finally:
            # Восстанавливаем оригинальные аргументы
            sys.argv = original_argv
    
    elif command == "prices":
        if len(sys.argv) < 3:
            print("Укажите ID таблицы: python run.py prices <spreadsheet_id>")
            sys.exit(1)
        
        # Создаем аргументы для скрипта
        import scripts.run_prices_report as prices_script
        
        # Парсим дополнительные аргументы
        script_args = ['run_prices_report.py', '--spreadsheet-id', sys.argv[2], '--overwrite']

        # Добавляем дополнительные аргументы если есть
        for i in range(3, len(sys.argv)):
            if sys.argv[i] != '--overwrite':  # не дублируем флаг
                script_args.append(sys.argv[i])
        
        # Сохраняем оригинальные аргументы
        original_argv = sys.argv
        sys.argv = script_args
        
        try:
            prices_script.main()
        finally:
            # Восстанавливаем оригинальные аргументы
            sys.argv = original_argv
    
    elif command == "ads":
        if len(sys.argv) < 3:
            print("Укажите ID таблицы: python run.py ads <spreadsheet_id>")
            sys.exit(1)
        
        # Создаем аргументы для скрипта
        import scripts.run_ads_report as ads_script
        
        # Парсим дополнительные аргументы
        script_args = ['run_ads_report.py', '--spreadsheet-id', sys.argv[2]]
        
        # Добавляем дополнительные аргументы если есть
        for i in range(3, len(sys.argv)):
            script_args.append(sys.argv[i])
        
        # Сохраняем оригинальные аргументы
        original_argv = sys.argv
        sys.argv = script_args
        
        try:
            ads_script.main()
        finally:
            # Восстанавливаем оригинальные аргументы
            sys.argv = original_argv
    

    elif command == "details":
        if len(sys.argv) < 3:
            print("Укажите ID таблицы: python run.py details <spreadsheet_id>")
            sys.exit(1)
    
        # Создаем аргументы для скрипта
        import scripts.run_details_report as details_script
    
        # Парсим дополнительные аргументы
        script_args = ['run_details_report.py', '--spreadsheet-id', sys.argv[2]]
    
        # Добавляем дополнительные аргументы если есть
        for i in range(3, len(sys.argv)):
            script_args.append(sys.argv[i])
    
        # Сохраняем оригинальные аргументы
        original_argv = sys.argv
        sys.argv = script_args
    
        try:
            details_script.main()
        finally:
            # Восстанавливаем оригинальные аргументы
            sys.argv = original_argv

    elif command == "sales-fbo":
        if len(sys.argv) < 3:
            print("Укажите ID таблицы: python run.py sales-fbo <spreadsheet_id>")
            sys.exit(1)
        import scripts.salesFBO as sales_fbo_script
        script_args = ['salesFBO.py', '--spreadsheet-id', sys.argv[2]]
        for i in range(3, len(sys.argv)):
            script_args.append(sys.argv[i])
        original_argv = sys.argv
        sys.argv = script_args
        try:
            sales_fbo_script.main()
        finally:
            sys.argv = original_argv

    elif command == "orders-fbo":
        if len(sys.argv) < 3:
            print("Укажите ID таблицы: python run.py orders-fbo <spreadsheet_id>")
            sys.exit(1)
        import scripts.ordersFBO as orders_fbo_script
        script_args = ['ordersFBO.py', '--spreadsheet-id', sys.argv[2]]
        for i in range(3, len(sys.argv)):
            script_args.append(sys.argv[i])
        original_argv = sys.argv
        sys.argv = script_args
        try:
            orders_fbo_script.main()
        finally:
            sys.argv = original_argv

    elif command == "stock-fbo":
        if len(sys.argv) < 3:
            print("Укажите ID таблицы: python run.py stock-fbo <spreadsheet_id>")
            sys.exit(1)
        import scripts.stockFBO as stock_fbo_script
        script_args = ['stockFBO.py', '--spreadsheet-id', sys.argv[2]]
        for i in range(3, len(sys.argv)):
            script_args.append(sys.argv[i])
        original_argv = sys.argv
        sys.argv = script_args
        try:
            stock_fbo_script.main()
        finally:
            sys.argv = original_argv

    elif command == "orders-fbs":
        if len(sys.argv) < 3:
            print("Укажите ID таблицы: python run.py orders-fbs <spreadsheet_id>")
            sys.exit(1)
        import scripts.ordersFBS as orders_fbs_script
        script_args = ['ordersFBS.py', '--spreadsheet-id', sys.argv[2]]
        for i in range(3, len(sys.argv)):
            script_args.append(sys.argv[i])
        original_argv = sys.argv
        sys.argv = script_args
        try:
            orders_fbs_script.main()
        finally:
            sys.argv = original_argv

    elif command == "stock-fbs":
        if len(sys.argv) < 3:
            print("Укажите ID таблицы: python run.py stock-fbs <spreadsheet_id>")
            sys.exit(1)
        import scripts.stockFBS as stock_fbs_script
        script_args = ['stockFBS.py', '--spreadsheet-id', sys.argv[2]]
        for i in range(3, len(sys.argv)):
            script_args.append(sys.argv[i])
        original_argv = sys.argv
        sys.argv = script_args
        try:
            stock_fbs_script.main()
        finally:
            sys.argv = original_argv

    elif command == "button":
        from scripts.button_handler import app
        app.run(debug=True, host='0.0.0.0', port=8080)
    
    elif command == "get-id":
        from scripts.get_spreadsheet_id import main as get_id_main
        get_id_main()
    
    else:
        print(f"Неизвестная команда: {command}")
        sys.exit(1)

if __name__ == "__main__":
    main()